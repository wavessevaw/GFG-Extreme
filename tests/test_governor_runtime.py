"""Governor v0.0.2 runtime: overlay application, confirmation, rollback, release."""
import asyncio
import hashlib
import logging
import os
import shutil
import sys
import tempfile
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "py_modules"))
TEMP_HOME = tempfile.mkdtemp(prefix="gfg-govrt-home-")
decky = types.ModuleType("decky")
decky.logger = logging.getLogger("decky-test")
decky.DECKY_USER_HOME = TEMP_HOME
sys.modules.setdefault("decky", decky)
HOME = sys.modules["decky"].DECKY_USER_HOME

from gfg_plugin.config_schema import ConfigurationManager  # noqa: E402
from gfg_plugin.configuration import ConfigurationService  # noqa: E402
from gfg_plugin.governor_overlay import OverlayStore  # noqa: E402
from gfg_plugin.governor_service import GovernorService  # noqa: E402

H = "I MAKO Renderer: present diagnostics: "


def fixed_plan(real, output):
    ratio = max(1, round(output / real)) - 1
    return (H + f"operation=fixed-plan generated_per_real={ratio} observed_output_fps={output} "
            "generated_presented=100 generated_skipped=0 configured_adaptive_target_fps=90 "
            "target_applies=0 display_budget_hz=90")


class FakeDisplay:
    def __init__(self):
        self.external = False

    def get_active_display_info(self):
        return {"success": True, "internal": not self.external, "external": self.external,
                "valid_rates": [60] if self.external else [90]}


class FakePower:
    def __init__(self, on_restore=None):
        self.state = type("S", (), {"available": True, "owned": False})()
        self.values = {"available": True, "owned": False, "observed_tdp_w": 15.0, "current_tdp_w": 15.0,
                       "ceiling_tdp_w": 15.0, "minimum_tdp_w": 3.0}
        self.on_restore = on_restore
        self.writes = []

    def status(self):
        return dict(self.values)

    def discover(self):
        return self.status()

    def claim(self):
        self.state.owned = True
        self.values["owned"] = True
        return self.status()

    def set_tdp_w(self, value):
        self.writes.append(value)
        self.values["observed_tdp_w"] = value
        self.values["current_tdp_w"] = value
        return {"success": True, "state": self.status()}

    def verify_ownership(self):
        return self.status()

    def restore_if_owned(self):
        was = self.state.owned
        if was and self.on_restore:
            self.on_restore()
        self.state.owned = False
        self.values["owned"] = False
        return {"success": True, "restored": was, "state": self.status()}


class FakeInspector:
    def __init__(self):
        self.info = {"running": True, "reason": "running", "pids": [1], "launch_key": [1, 1, 1],
                     "renderer_loaded": True, "governor_launch": {"scaling": 0, "rev": 1, "owner": 1},
                     "saved_scaling_at_launch": False}

    def live_launch(self, profile):
        return dict(self.info)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class RuntimeBase(unittest.TestCase):
    def setUp(self):
        shutil.rmtree(HOME, ignore_errors=True)
        os.makedirs(HOME)
        self.cfg = ConfigurationService()
        self.assertTrue(self.cfg.create_profile("game", "mako")["success"])
        self.assertTrue(self.cfg.set_current_profile("game")["success"])
        self.saved_hash = sha(self.cfg.config_file_path)
        self.display = FakeDisplay()
        self.inspector = FakeInspector()
        self.svc = GovernorService(self.cfg, self.display, logging.getLogger("gov-rt"), self.inspector)
        self.svc.power = FakePower()
        self.t = {"now": 100.0}
        self.svc.observer.time_fn = lambda: self.t["now"]
        self.svc._last_display_poll = -1e9
        self.assertIsNone(self.svc.set_enabled("game", True).get("overlay_error"))

    def tearDown(self):
        self.assertEqual(sha(self.cfg.config_file_path), self.saved_hash, "Saved config was modified")

    # -- helpers
    def step(self, seconds=1.0):
        self.t["now"] += seconds
        self.svc._last_display_poll = -1e9 if self.display.external != self.svc._last_display.get("external") else self.svc._last_display_poll
        asyncio.run(self.svc._iteration())
        return self.svc.get_status()

    def feed(self, count, real, output, dt=0.6):
        for _ in range(count):
            self.t["now"] += dt
            self.svc.observer.consume_line(fixed_plan(real, output), now=self.t["now"])

    def overlay_profile(self):
        text = Path(self.svc.overlay.path_for("game")).read_text()
        return ConfigurationManager.parse_toml_content_multi_profile(text)["profiles"]["game"]

    def header(self):
        return self.svc.overlay.read_header("game")

    def prime_not_matching(self):
        """Running 60 FPS native: proves 45x2 capacity but is not any proven point."""
        self.feed(20, 60, 60)
        self.t["now"] += 0.5


class TrialFlowTests(RuntimeBase):
    def test_ladder_rejects_unhealthy_point_rolls_back_then_confirms_next(self):
        self.prime_not_matching()
        st = self.step()
        self.assertEqual(st["state"], "APPLY")
        self.assertEqual(st["request"]["point"], "native90")
        # Native trial: renderer keeps showing 60 FPS native cadence -> below cap.
        self.feed(16, 60, 60)
        st = self.step()
        self.assertEqual(st["ladder"]["rejected"].get("native90"), "real-cadence-below-cap")
        self.assertIsNone(st["request"])
        self.assertEqual(self.overlay_profile()["frame_generation_enabled"],
                         self.cfg.get_profile_config("game")["config"]["frame_generation_enabled"])
        # Next iteration tries 45x2.
        st = self.step()
        self.assertEqual(st["request"]["point"], "45x2")
        prof = self.overlay_profile()
        self.assertEqual((prof["multiplier"], prof["base_fps_cap"], prof["adaptive"]), (2, 45, False))
        self.feed(16, 45, 90)
        st = self.step()
        self.assertEqual(st["state"], "PLAN")
        self.assertEqual(st["reason"], "operating-point-confirmed")
        self.assertEqual(st["active_point"]["key"], "45x2")
        self.assertEqual(st["active_point_mode"], "applied")
        # Only now does power optimisation start.
        self.feed(4, 45, 90)
        st = self.step()
        self.assertEqual(st["state"], "OPTIMIZE_POWER")
        self.assertTrue(self.svc.power.state.owned)

    def test_write_alone_is_not_application_timeout_rolls_back(self):
        self.prime_not_matching()
        self.step()
        self.assertEqual(self.svc.get_status()["request"]["point"], "native90")
        rev_before = self.header()["rev"]
        st = self.step(self.svc.CONFIRM_TIMEOUT_SECONDS + 1)  # renderer stays silent
        self.assertEqual(st["ladder"]["rejected"]["native90"], "confirmation-timeout")
        self.assertGreater(self.header()["rev"], rev_before)  # rollback overlay written
        self.assertIsNone(st["request"])
        self.assertFalse(self.svc.power.state.owned)

    def test_event_seq_and_sample_seq_are_not_confused(self):
        # Many non-FPS events: event_seq runs far ahead of sample_seq.
        for _ in range(200):
            self.t["now"] += 0.01
            self.svc.observer.consume_line(H + "operation=present-breakdown total_ms=11", now=self.t["now"])
        self.prime_not_matching()
        self.assertGreater(self.svc.observer.event_seq, self.svc.observer.sample_seq + 150)
        self.step()
        self.assertEqual(self.svc.get_status()["request"]["point"], "native90")
        self.feed(16, 90, 90)  # native 90 healthy
        st = self.step()
        self.assertEqual(st["active_point"]["key"], "native90")

    def test_pre_write_samples_never_confirm_a_new_point(self):
        self.prime_not_matching()
        self.step()  # request native90
        self.feed(16, 60, 60)
        self.step()  # rejected
        self.step()  # request 45x2 now pending
        self.assertEqual(self.svc.get_status()["request"]["point"], "45x2")
        # 20 old 60 FPS native samples exist in the observer; none postdate the mark.
        st = self.step(2.0)
        self.assertEqual(st["state"], "APPLY")
        self.assertIsNone(st["active_point"])

    def test_renderer_transition_failure_rolls_back_immediately(self):
        self.prime_not_matching()
        self.step()
        self.t["now"] += 0.5
        self.svc.observer.consume_line(H + "operation=runtime-transition-failed reason=x", now=self.t["now"])
        st = self.step()
        self.assertEqual(st["ladder"]["rejected"]["native90"], "renderer-transition-failed")

    def test_bounded_ladder_ends_in_not_viable_and_restores_base(self):
        self.prime_not_matching()
        for _ in range(14):
            self.feed(2, 20, 20)
            st = self.step()
            if st["request"]:
                self.feed(16, 20, 20)  # every point looks bad (20 FPS native-ish cadence)
            if st.get("reason") == "target-not-proven-viable":
                break
        self.feed(2, 20, 20)
        st = self.step()
        self.assertEqual(st["reason"], "target-not-proven-viable")
        self.assertLessEqual(st["ladder"]["attempts"], 6)
        # Scaled points were skipped (engine not provisioned at launch), never rejected as a trial.
        self.assertTrue(all(v == "scaling-engine-not-provisioned-at-launch" for v in st["ladder"]["skipped"].values()))
        saved = self.cfg.get_profile_config("game")["config"]
        self.assertEqual(self.overlay_profile()["multiplier"], saved["multiplier"])
        # No re-trial storm: stays put.
        attempts = st["ladder"]["attempts"]
        for _ in range(3):
            self.feed(2, 20, 20)
            st = self.step()
        self.assertEqual(st["ladder"]["attempts"], attempts)

    def test_relaunch_required_when_game_was_not_launched_with_overlay(self):
        self.inspector.info["governor_launch"] = None
        self.prime_not_matching()
        rev = self.header()["rev"]
        st = self.step()
        self.assertEqual(st["reason"], "relaunch-required-for-governor-overlay")
        self.assertIsNone(st["request"])
        self.assertEqual(self.header()["rev"], rev)


class AdoptionTests(RuntimeBase):
    def test_already_running_proven_point_is_adopted_without_overlay_change(self):
        self.feed(20, 48, 96)
        self.t["now"] += 0.5
        rev = self.header()["rev"]
        st = self.step()
        self.assertEqual(st["active_point"]["key"], "45x2")
        self.assertEqual(st["active_point_mode"], "adopted")
        self.assertEqual(self.header()["rev"], rev)
        st = self.step()
        self.assertEqual(st["state"], "OPTIMIZE_POWER")


class ReleaseTests(RuntimeBase):
    def apply_45x2(self):
        self.prime_not_matching()
        self.step()
        self.feed(16, 60, 60)
        self.step()
        self.step()
        self.feed(16, 45, 90)
        st = self.step()
        self.assertEqual(st["active_point"]["key"], "45x2")
        self.feed(4, 45, 90)
        self.step()
        self.assertTrue(self.svc.power.state.owned)

    def test_disable_restores_overlay_before_power_ownership_is_released(self):
        seen = {}

        def at_power_restore():
            seen["header"] = self.header()
            seen["profile"] = self.overlay_profile()

        self.svc.power.on_restore = at_power_restore
        self.apply_45x2()
        self.assertEqual(self.overlay_profile()["multiplier"], 2)
        self.svc.set_enabled("game", False)
        st = self.step()
        self.assertEqual(st["state"], "DISABLED")
        self.assertEqual(seen["header"]["owner"], 0)  # lease released
        saved = self.cfg.get_profile_config("game")["config"]
        self.assertEqual(seen["profile"]["multiplier"], saved["multiplier"])
        self.assertEqual(seen["profile"]["base_fps_cap"], saved["base_fps_cap"])
        self.assertFalse(self.svc.power.state.owned)
        self.assertIsNone(self.svc.get_status()["active_point"])

    def test_restore_failure_keeps_ownership_and_retries(self):
        self.apply_45x2()
        real_replace = self.svc.overlay._replace
        self.svc.overlay._replace = lambda a, b: (_ for _ in ()).throw(OSError("disk full"))
        result = self.svc.set_enabled("game", False)
        self.assertIn("overlay_error", result)
        st = self.step()
        self.assertEqual(st["reason"], "overlay-restore-failed")
        self.assertTrue(self.svc.power.state.owned, "power must not be released before Saved is restored")
        self.assertIn("game", st["restore_pending"])
        self.svc.overlay._replace = real_replace
        st = self.step()
        st = self.step()
        self.assertEqual(st["state"], "DISABLED")
        self.assertFalse(self.svc.power.state.owned)
        self.assertEqual(self.header()["owner"], 0)
        self.assertNotIn("restore_pending", self.svc.get_status())

    def test_profile_switch_releases_old_profile_overlay_and_power(self):
        self.apply_45x2()
        self.assertTrue(self.cfg.create_profile("other", "mako")["success"])
        self.assertTrue(self.cfg.set_current_profile("other")["success"])
        self.saved_hash = sha(self.cfg.config_file_path)  # user-driven Saved changes
        self.feed(2, 45, 90)
        st = self.step()
        self.assertEqual(st["profile"], "other")
        self.assertFalse(self.svc.power.state.owned)
        self.assertEqual(self.header()["owner"], 0)
        saved = self.cfg.get_profile_config("game")["config"]
        self.assertEqual(self.overlay_profile()["multiplier"], saved["multiplier"])
        self.assertIsNone(self.svc.get_status()["active_point"])

    def test_plugin_stop_restores_overlay_then_power(self):
        self.apply_45x2()
        asyncio.run(self.svc.stop())
        self.assertEqual(self.header()["owner"], 0)
        saved = self.cfg.get_profile_config("game")["config"]
        self.assertEqual(self.overlay_profile()["multiplier"], saved["multiplier"])
        self.assertFalse(self.svc.power.state.owned)

    def test_rollback_write_failure_is_retried(self):
        self.prime_not_matching()
        self.step()
        real_replace = self.svc.overlay._replace
        self.svc.overlay._replace = lambda a, b: (_ for _ in ()).throw(OSError("io"))
        st = self.step(self.svc.CONFIRM_TIMEOUT_SECONDS + 1)
        self.assertEqual(st["reason"], "rollback-failed")
        self.svc.overlay._replace = real_replace
        st = self.step(self.svc.ROLLBACK_RETRY_SECONDS + 1)
        st = self.step()
        self.assertNotEqual(st["reason"], "rollback-failed")

    def test_new_telemetry_generation_resets_applied_point(self):
        self.apply_45x2()
        self.svc.observer._session_generation += 1  # log rotated: new game session
        st = self.step()
        self.assertEqual(st["reason"], "new-game-session")
        self.assertIsNone(st["active_point"])
        saved = self.cfg.get_profile_config("game")["config"]
        self.assertEqual(self.overlay_profile()["multiplier"], saved["multiplier"])
        self.assertFalse(self.svc.power.state.owned)

    def test_new_launch_resets_applied_point(self):
        self.apply_45x2()
        self.inspector.info["launch_key"] = [2, 2, 2]
        self.svc._launch_polled = -1e9
        st = self.step()
        self.assertEqual(st["reason"], "new-game-session")
        self.assertIsNone(st["active_point"])

    def test_dock_switch_invalidates_point(self):
        self.apply_45x2()
        self.display.external = True
        self.svc._last_display_poll = -1e9
        st = self.step()
        self.assertEqual(st["reason"], "display-mode-changed")
        self.assertIsNone(st["active_point"])
        self.assertFalse(self.svc.power.state.owned)

    def test_external_backend_selected_releases_overlay_point(self):
        self.apply_45x2()
        self.cfg.update_profile_config_fields("game", {"fg_backend": "optiscaler"})
        self.saved_hash = sha(self.cfg.config_file_path)  # user-driven Saved change
        st = self.step()
        self.assertEqual(st["state"], "OBSERVE_ONLY")
        self.assertIsNone(st["active_point"])
        self.assertFalse(self.svc.power.state.owned)
        self.assertEqual(self.overlay_profile()["multiplier"], self.cfg.get_profile_config("game")["config"]["multiplier"])


class OverlayHousekeepingTests(RuntimeBase):
    def test_saved_edit_during_session_is_projected_into_overlay(self):
        self.feed(20, 48, 96)
        self.step()
        self.cfg.update_profile_config_fields("game", {"flow_scale": 0.6})
        self.saved_hash = sha(self.cfg.config_file_path)  # the user edited Saved; that is allowed
        self.step()
        self.assertAlmostEqual(self.overlay_profile()["flow_scale"], 0.6)

    def test_startup_reconcile_refreshes_lease_for_enabled_and_restores_disabled(self):
        self.svc.set_enabled("game", False)
        self.assertEqual(self.header()["owner"], 0)
        other = GovernorService(self.cfg, self.display, logging.getLogger("gov-rt2"), self.inspector)
        other.power = FakePower()
        other.set_enabled("game", True)
        stale = OverlayStore(self.cfg.config_dir, self.cfg.build_governor_overlay_text, owner_pid=999999)
        stale.write("game", {}, point_key="45x2")
        other._reconcile_overlays()
        self.assertEqual(other.overlay.read_header("game")["owner"], os.getpid())

    def test_enable_writes_base_overlay_immediately_for_next_launch(self):
        self.assertTrue(self.svc.overlay.exists("game"))
        self.assertEqual(self.header()["owner"], os.getpid())


class DeviceTargetRuntimeTests(RuntimeBase):
    def test_lcd_handheld_targets_60_and_first_trial_is_native60(self):
        self.svc._device = {"model": "lcd", "product": "Jupiter"}
        self.feed(20, 40, 40)
        self.t["now"] += 0.5
        st = self.step()
        self.assertEqual(st["target_output_fps"], 60)
        self.assertEqual(st["device"]["mode"], "lcd")
        self.assertEqual(st["request"]["point"], "native60")
        prof = self.overlay_profile()
        self.assertEqual((prof["base_fps_cap"], prof["target_fps"]), (60, 60))

    def test_oled_handheld_targets_90_and_dock_targets_60(self):
        self.svc._device = {"model": "oled", "product": "Galileo"}
        self.feed(20, 40, 40)
        self.assertEqual(self.step()["target_output_fps"], 90)
        self.assertEqual(self.svc.get_status()["device"]["mode"], "oled")


if __name__ == "__main__":
    unittest.main()
