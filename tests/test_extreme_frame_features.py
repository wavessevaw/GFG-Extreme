"""Native settings must be independent, reversible and acknowledged before active status."""
import logging
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "py_modules"))
from gfg_plugin import extreme
from gfg_plugin.governor_service import GovernorService
from gfg_plugin.frame_os.runner import FrameOsRunner
from gfg_plugin.frame_os.control_channel import ControlChannel
from gfg_plugin.frame_os.input_sensor import EvdevReader


class FeatureStatusTests(unittest.TestCase):
    def facts(self, **overrides):
        runner = {"mode": "act", "acknowledged": True, "latency_enabled": True,
                  "stall_shield_enabled": True, "telemetry": {"live": True,
                      "features": {"tick_shaping": True, "stall_shield": True},
                      "active_features": {"tick_shaping": True, "stall_shield": True}}}
        runner.update(overrides.pop("runner", {}))
        pacing = extreme.pacing_facts({"latency": True, "shield": True}, runner,
                                     mode="act", paused=False)
        pacing.update(overrides)
        return {"running": True, "pacing": pacing}

    def state(self, feature="shield", **kwargs):
        return extreme.pacing_booster(feature, self.facts(**kwargs))

    def test_only_native_ack_and_active_bit_are_active(self):
        self.assertEqual(self.state()["state"], "active")
        self.assertEqual(self.state(ack=False)["state"], "waiting")
        self.assertEqual(self.state(active={})["state"], "waiting")
        self.assertEqual(self.state(published={"shield": False})["state"], "waiting")

    def test_old_native_layer_requires_upgrade_even_with_generation_ack(self):
        self.assertEqual(self.state(support={})["reason"], "pacer-feature-upgrade-required")

    def test_off_mode_pause_and_missing_pacer_are_distinct(self):
        self.assertEqual(self.state(settings={"shield": False})["state"], "off")
        self.assertEqual(self.state(mode="shadow")["state"], "off")
        self.assertEqual(self.state(paused=True)["state"], "ready")
        self.assertEqual(self.state(live=False)["state"], "restart_required")

    def test_game_learning_and_ab_control_do_not_claim_active_timing(self):
        self.assertEqual(self.state("latency", shaping_off=True)["state"], "off")
        self.assertEqual(self.state("latency", control="no-shaping")["state"], "waiting")

    def test_stale_mode_ack_is_not_accepted(self):
        self.assertEqual(self.state(runner={"mode": "shadow"})["state"], "waiting")

    def test_no_game_is_waiting(self):
        facts = self.facts()
        facts["running"] = False
        self.assertEqual(extreme.pacing_booster("shield", facts)["state"], "waiting")


class FeatureSettingsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.service = GovernorService(SimpleNamespace(config_dir=root,
                         runtime_state_dir=root / "runtime-state"), None, logging.getLogger("test-features"))
        self.service._save_settings = Mock()
        self.service._poke = Mock()

    def test_defaults_preserve_existing_timing_and_leave_shield_opt_in(self):
        self.assertEqual(self.service.frame_os_features("Game"), {"latency": True, "shield": False})

    def test_independent_profile_settings(self):
        self.assertTrue(self.service.set_frame_os_feature("Game", "shield", True)["success"])
        self.service.set_frame_os_feature("Game", "latency", False)
        self.assertEqual(self.service.frame_os_features("Game"), {"latency": False, "shield": True})
        self.assertEqual(self.service.frame_os_features("Other"), {"latency": True, "shield": False})

    def test_invalid_input_does_not_write(self):
        for feature, value in (("unknown", True), ("shield", "false"), ("latency", 0)):
            self.assertFalse(self.service.set_frame_os_feature("Game", feature, value)["success"])
        self.service._save_settings.assert_not_called()

    def test_failed_save_restores_the_previous_preference(self):
        self.service.set_frame_os_feature("Game", "shield", True)
        self.service._save_settings.side_effect = OSError("disk full")
        self.assertFalse(self.service.set_frame_os_feature("Game", "shield", False)["success"])
        self.assertTrue(self.service.frame_os_features("Game")["shield"])

    def test_service_passes_current_flags_to_runner(self):
        service = self.service
        service._settings = {"frame_os_act_unlocked": True, "profiles": {"Game": {
            "frame_os": "act", "frame_os_features": {"latency": False, "shield": True}}}}
        service._budget = SimpleNamespace(point=SimpleNamespace(target_output_fps=90, base_target_fps=30),
                                          tdp=15, tdp_control=True)
        service._point = {}
        service._status["enabled"] = True
        service._menu_covering = lambda: False
        service._trusted_game_focus = lambda: True
        service._sync_frame_os_memory = lambda profile: None
        with patch.object(service.frame_os, "configure") as configure:
            service._configure_frame_os("Game")
            self.assertFalse(configure.call_args.kwargs["latency_enabled"])
            self.assertTrue(configure.call_args.kwargs["stall_shield_enabled"])


class FeaturePolicyTests(unittest.TestCase):
    def test_live_toggle_republishes_native_flags_without_resetting_cadence(self):
        with tempfile.TemporaryDirectory() as temp:
            runner = FrameOsRunner(ControlChannel(Path(temp) / "control"),
                                   reader_factory=lambda: EvdevReader())
            self.addCleanup(runner.close)
            def configure(latency, shield):
                runner.configure(enabled=True, mode="act", output_hz=90,
                                 calm_real_hz=30, max_multiplier=3, calm_w=15,
                                 latency_enabled=latency, stall_shield_enabled=shield)
            configure(True, True)
            with patch.object(runner.channel, "write_policy", wraps=runner.channel.write_policy) as write:
                runner.tick(1)
                self.assertTrue(write.call_args.kwargs["tick_shaping"])
                self.assertTrue(write.call_args.kwargs["stall_shield"])
                generation = runner.generation
                policy = runner.policy
                configure(False, False)
                runner.tick(2)
                self.assertFalse(write.call_args.kwargs["tick_shaping"])
                self.assertFalse(write.call_args.kwargs["stall_shield"])
                self.assertGreater(runner.generation, generation)
                self.assertIs(runner.policy, policy)


if __name__ == "__main__":
    unittest.main()
