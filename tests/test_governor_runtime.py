"""Governor v0.0.2 runtime: overlay application, confirmation, rollback, release."""
import asyncio
import hashlib
import json
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


def adaptive_plan(real, output):
    """Adaptive-mode line (how a fractional ratio is reported): interval means carry the ratio."""
    return (H + f"operation=adaptive-plan base_fps={real} target_fps={output} generated=1 "
            f"source_interval_mean_ms={1000.0 / real:.3f} requested_interval_mean_ms={1000.0 / output:.3f}")


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
                       "ceiling_tdp_w": 15.0, "initial_tdp_w": 12.0, "minimum_tdp_w": 3.0}
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
        self.svc.DEFAULT_MODE = "quality"  # the v0.0.2 ladder; budget mode has its own tests
        self.svc.PREDICTIVE_SKIP = False
        self.svc.hud.MIN_REWRITE_S = 0.0  # MangoHud rewrite rate limit has its own tests  # these tests walk the full ladder; see PredictiveStartTests
        self.t = {"now": 100.0}
        self.svc.observer.time_fn = lambda: self.t["now"]
        self.svc._last_display_poll = -1e9
        self.assertIsNone(self.svc.set_enabled("game", True).get("overlay_error"))

    def tearDown(self):
        self.assertEqual(sha(self.cfg.config_file_path), self.saved_hash, "Saved config was modified")

    def test_hud_set_publishes_and_removes_active_config(self):
        from gfg_plugin.governor_hud import active_config_path, status_path
        active = active_config_path(self.cfg.config_dir)
        # Governor on: a hidden HUD config is published for the next launches.
        self.assertIn("no_display=1", active.read_text())
        result = self.svc.set_hud("game", True, "detailed", "top-right")
        self.assertTrue(result["success"])
        self.assertTrue(active.is_file())
        text = active.read_text()
        self.assertIn("position=top-right", text)
        self.assertIn("exec=cat " + str(status_path(self.cfg.config_dir)), text)
        self.assertEqual(self.svc.get_status("game")["hud"], {"enabled": True, "preset": "detailed", "position": "top-right"})
        self.step()
        self.assertIn("sc100", status_path(self.cfg.config_dir).read_text())
        self.svc.set_hud("game", False)
        # Hidden, not removed: MangoHud stays loaded at launch and re-reads it.
        self.assertIn("no_display=1", active.read_text())
        # bogus values are normalised, never written raw
        self.svc.set_hud("game", True, "evil;rm", "nowhere")
        self.assertEqual(self.svc.hud_settings("game")["preset"], "standard")
        self.assertEqual(self.svc.hud_settings("game")["position"], "top-right")

    def test_idle_when_nothing_enabled_and_busy_when_enabled(self):
        self.assertFalse(self.svc._is_idle())          # enabled in setUp
        self.svc.set_enabled("game", False)
        self.step()
        self.assertTrue(self.svc._is_idle())
        self.svc.set_hud("game", True)
        self.assertFalse(self.svc._is_idle())          # HUD status needs the loop
        self.svc.set_hud("game", False)
        self.assertTrue(self.svc._is_idle())

    def test_loop_wakes_immediately_when_poked_while_idle(self):
        async def scenario():
            self.svc.set_enabled("game", False)
            self.svc.IDLE_LOOP_SECONDS = 30.0
            calls = []
            original = self.svc._iteration
            async def counting():
                calls.append(1)
                await original()
            self.svc._iteration = counting
            await self.svc.start()
            await asyncio.sleep(0.3)
            idle_calls = len(calls)
            await asyncio.sleep(0.3)
            self.assertEqual(len(calls), idle_calls, "idle loop must not spin")
            await asyncio.to_thread(self.svc.set_enabled, "game", True)  # worker-thread poke
            await asyncio.sleep(0.5)
            woke = len(calls) > idle_calls
            await self.svc.stop()
            return woke
        self.assertTrue(asyncio.run(scenario()))

    # -- helpers
    def step(self, seconds=1.0):
        self.t["now"] += seconds
        self.svc._last_display_poll = -1e9 if self.display.external != self.svc._last_display.get("external") else self.svc._last_display_poll
        asyncio.run(self.svc._iteration())
        return self.svc.get_status()

    def feed_adaptive(self, count, real, output, dt=0.6):
        for _ in range(count):
            self.t["now"] += dt
            self.svc.observer.consume_line(adaptive_plan(real, output), now=self.t["now"])

    def feed(self, count, real, output, dt=0.6):
        for _ in range(count):
            self.t["now"] += dt
            self.svc.observer.consume_line(fixed_plan(real, output), now=self.t["now"])

    def overlay_profile(self):
        text = Path(self.svc.overlay.path_for("game")).read_text()
        return ConfigurationManager.parse_toml_content_multi_profile(text)["profiles"]["game"]

    def header(self):
        return self.svc.overlay.read_header("game")

    FRACTIONAL_RUNGS = ("72x1.25", "60x1.5", "51x1.75")

    def reject_fractional(self, key="60x1.5"):
        """The pending fractional request is never confirmed -> timeout, rollback, rejected."""
        self.assertEqual(self.svc.get_status()["request"]["point"], key)
        st = self.step(self.svc.CONFIRM_TIMEOUT_SECONDS + 1)
        self.assertEqual(st["ladder"]["rejected"][key], "confirmation-timeout")
        self.feed(20, 60, 60)            # fresh telemetry after the long wait (clock moved on)
        self.t["now"] += 0.5

    def reject_all_fractionals(self):
        """Every fractional rung below x2 (x1.25, x1.5, x1.75) times out in turn."""
        for key in self.FRACTIONAL_RUNGS:
            self.step()
            self.reject_fractional(key)

    def prime_not_matching(self):
        """Running 60 FPS native: proves 45x2 capacity but is not any proven point."""
        self.feed(20, 60, 60)
        self.t["now"] += 0.5


class PredictiveStartTests(RuntimeBase):
    def test_native_60_for_90_target_starts_at_a_feasible_point(self):
        self.svc.PREDICTIVE_SKIP = True
        self.prime_not_matching()
        st = self.step()
        self.assertEqual(st["state"], "APPLY")
        self.assertEqual(st["request"]["point"], "60x1.5")  # native90 and 72x1.25 need >66 real fps
        self.assertEqual(st["ladder"]["rejected"], {})
        self.assertIn("native90", st["ladder"]["predicted_infeasible"])


class ModeTests(RuntimeBase):
    def test_balanced_mode_is_accepted_and_builds_a_balanced_controller(self):
        self.assertTrue(self.svc.set_mode("game", "balanced")["success"])
        self.assertEqual(self.svc.get_status("game")["mode"], "balanced")
        self.assertFalse(self.svc.set_mode("game", "turbo")["success"])
        self.prime_not_matching()
        self.step()
        self.step()
        budget = self.svc.get_status("game").get("budget")
        self.assertIsNotNone(budget)
        self.assertEqual(budget["flavor"], "balanced")

    def prime_not_matching(self):
        self.feed(20, 60, 60)
        self.t["now"] += 0.5


class BottleneckAwareLadderTests(RuntimeBase):
    def test_cpu_bound_game_skips_render_scale_points(self):
        self.svc.sensors.sample = lambda force=False: {"gpu_busy_pct": 40.0, "cpu_top_core_pct": 98.0}
        self.prime_not_matching()
        self.step()  # sensors/diagnosis are refreshed at the end of every iteration
        self.assertEqual(self.svc._status["diagnosis"]["bottleneck"], "cpu")
        ladder = self.svc._ladder
        self.assertIsNotNone(ladder)
        for point in ladder.candidates():  # force the search to reach the scaled rungs
            if point.render_scale_pct == 100:
                ladder.reject(point.key, "test")
        self.svc._request = None
        self.step()
        skipped = (self.svc.get_status("game").get("ladder") or {}).get("skipped", {})
        scaled = {k: v for k, v in skipped.items() if "-s9" in k or "-s8" in k}
        self.assertTrue(scaled, skipped)
        self.assertTrue(all(v == "cpu-bound-render-scale-does-not-help" for v in scaled.values()), skipped)


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
        # Next iterations try x1.25, x1.5 and x1.75; this renderer cannot reach
        # any of them (stays a 2x cadence) so each confirmation times out.
        self.reject_all_fractionals()
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

    def test_quality_rejects_a_deeper_delivered_ratio_in_seconds(self):
        """Field log: 40x2.25 waited the full 25 s while x2 was delivered."""
        self.prime_not_matching()
        self.step()                                  # native90 trial
        self.feed(16, 60, 60)
        self.step()                                  # rejected: real below cap
        st = self.step()
        self.assertEqual(st["request"]["point"], "72x1.25")
        started = self.t["now"]
        self.svc.observer.consume_line(
            H + "operation=runtime-state-applied role=frame-generation state_revision=99 transition=live "
            "frame_generation_enabled=1 adaptive=1 target_fps=90 multiplier=1.25 base_fps_cap=72 "
            "frame_generation_resources_available=1 generated_frame_capacity=2", now=self.t["now"])
        self.feed(16, 45, 90)                        # the renderer holds 90 at x2 instead
        st = self.step()
        self.assertEqual(st["ladder"]["rejected"].get("72x1.25"), "delivered-deeper-ratio")
        self.assertLess(self.t["now"] - started, 15.0)

    def test_quality_failures_survive_a_new_ladder(self):
        """A mode switch or reload builds a new ladder; it must not retry what just failed."""
        self.prime_not_matching()
        self.step()
        self.feed(16, 60, 60)
        st = self.step()
        self.assertEqual(st["ladder"]["rejected"].get("native90"), "real-cadence-below-cap")
        self.svc._ladder = None                      # as after a mode switch
        self.feed(20, 60, 60)
        self.t["now"] += 0.5
        st = self.step()
        self.assertEqual(self.svc._ladder.rejected.get("native90"), "remembered-failure")
        self.assertNotEqual(st["request"]["point"], "native90")

    def test_point_unhealthy_at_ceiling_is_rejected_and_ladder_moves_on(self):
        self.prime_not_matching()
        self.step()
        self.feed(16, 60, 60)
        self.step()
        self.reject_all_fractionals()
        self.step()                      # 45x2 trial
        self.feed(16, 45, 90)
        st = self.step()
        self.assertEqual(st["active_point"]["key"], "45x2")
        self.feed(4, 45, 90)
        st = self.step()
        self.assertEqual(st["state"], "OPTIMIZE_POWER")
        # At the user's TDP the game cannot hold 45 real: one bad window is re-checked ...
        self.feed(16, 38, 76)
        st = self.step()
        self.assertEqual(st["reason"], "rechecking-at-ceiling")
        self.assertEqual(st["active_point"]["key"], "45x2")
        # ... the second rejects the point instead of parking at the ceiling for the session.
        self.feed(16, 38, 76)
        st = self.step()
        self.assertEqual(st["ladder"]["rejected"].get("45x2"), "not-healthy-at-ceiling")
        self.assertIsNone(st["active_point"])
        self.assertFalse(self.svc.power.state.owned)
        self.assertEqual(self.svc.power.writes, [])
        st = self.step()
        self.assertEqual(st["state"], "APPLY")
        self.assertNotEqual(st["request"]["point"], "45x2")
        # Not for the whole session: a cutscene must not cost the point forever.
        ladder = self.svc._ladder
        ladder.attempts = 0
        self.assertIn("45x2", ladder.rejected)
        ladder.next_point(lambda p: None, now=self.svc._clock() + self.svc.CEILING_REJECT_TTL_S + 1)
        self.assertNotIn("45x2", ladder.rejected)
        self.assertIn("native90", ladder.rejected)  # other rejections stay

    def test_fractional_x15_is_tried_before_x2_and_confirmed_on_real_ratio(self):
        self.prime_not_matching()
        self.step()                      # native90 trial
        self.feed(16, 60, 60)
        self.step()                      # native rejected
        self.step()                      # x1.25 trial
        self.reject_fractional("72x1.25")
        st = self.step()                 # x1.5 trial
        self.assertEqual(st["request"]["point"], "60x1.5")
        prof = self.overlay_profile()
        self.assertEqual((prof["adaptive"], prof["target_fps"], prof["base_fps_cap"]), (True, 90, 60))
        self.assertFalse(prof["adaptive_auto_base_fps_cap"])
        self.assertFalse(prof["adaptive_stable_cadence"])
        self.assertTrue(prof["frame_generation_enabled"])
        self.feed_adaptive(16, 60, 90)   # real 60 -> output 90 = x1.5 on the real ratio
        st = self.step()
        self.assertEqual(st["reason"], "operating-point-confirmed")
        self.assertEqual(st["active_point"]["key"], "60x1.5")
        self.assertEqual(st["active_point"]["multiplier"], 1.5)

    def test_x175_is_confirmed_on_its_real_ratio(self):
        self.prime_not_matching()
        self.step()
        self.feed(16, 60, 60)
        self.step()
        for key in self.FRACTIONAL_RUNGS[:2]:
            self.step()
            self.reject_fractional(key)
        st = self.step()
        self.assertEqual(st["request"]["point"], "51x1.75")
        prof = self.overlay_profile()
        self.assertEqual((prof["adaptive"], prof["target_fps"], prof["base_fps_cap"]), (True, 90, 51))
        self.assertEqual(prof["adaptive_max_multiplier"], 2)
        self.feed_adaptive(16, 51, 90)   # ratio 1.76
        st = self.step()
        self.assertEqual(st["reason"], "operating-point-confirmed")
        self.assertEqual(st["active_point"]["key"], "51x1.75")

    def test_neighbouring_fraction_does_not_confirm_a_point(self):
        """x1.5 cadence while x1.75 is pending: 0.25 apart, must not be accepted."""
        self.prime_not_matching()
        self.step()
        self.feed(16, 60, 60)
        self.step()
        for key in self.FRACTIONAL_RUNGS[:2]:
            self.step()
            self.reject_fractional(key)
        self.step()
        self.assertEqual(self.svc.get_status()["request"]["point"], "51x1.75")
        self.feed_adaptive(16, 60, 90)   # ratio 1.5
        st = self.step()
        self.assertEqual(st["state"], "APPLY")
        self.assertIsNone(st["active_point"])

    def test_integer_cadence_does_not_confirm_fractional_point(self):
        self.prime_not_matching()
        self.step()
        self.feed(16, 60, 60)
        self.step()
        self.step()                      # 60x1.5 pending
        self.feed(16, 45, 90)            # renderer settled on x2: ratio 2.0 != 1.5
        st = self.step()
        self.assertEqual(st["state"], "APPLY")
        self.assertIsNone(st["active_point"])

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
        self.step()  # request 72x1.25 now pending
        self.assertEqual(self.svc.get_status()["request"]["point"], "72x1.25")
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
        for _ in range(40):
            self.feed(2, 20, 20)
            st = self.step()
            if st["request"]:
                self.feed(16, 20, 20)  # every point looks bad (20 FPS native-ish cadence)
            if st.get("reason") == "target-not-proven-viable":
                break
        self.feed(2, 20, 20)
        st = self.step()
        self.assertEqual(st["reason"], "target-not-proven-viable")
        self.assertLessEqual(st["ladder"]["attempts"], 12)
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

    def test_game_started_before_governor_says_relaunch_instead_of_waiting(self):
        # Field log: Governor enabled mid-game -> no diagnostics, no FPS ever.
        self.inspector.info["governor_launch"] = None
        st = self.step()
        self.assertEqual(st["state"], "PAUSED")
        self.assertEqual(st["reason"], "relaunch-required-for-governor-overlay")
        self.assertEqual(st["capability"]["reason"], "relaunch-required-for-governor-overlay")

    def test_no_events_with_governor_launch_keeps_telemetry_reason(self):
        st = self.step()
        self.assertEqual(st["state"], "PAUSED")
        self.assertNotIn(st["reason"], ("relaunch-required-for-governor-overlay", "game-not-running"))


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
        self.reject_all_fractionals()
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
        self.assertEqual(seen["header"]["owner"], os.getpid())  # standby: lease kept for live re-enable
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
        self.assertEqual(self.header()["owner"], os.getpid())
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
        self.assertEqual(self.header()["owner"], os.getpid())
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
        self.assertEqual(self.header()["owner"], os.getpid())
        other = GovernorService(self.cfg, self.display, logging.getLogger("gov-rt2"), self.inspector)
        other.power = FakePower()
        other.DEFAULT_MODE = "quality"
        other.set_enabled("game", True)
        stale = OverlayStore(self.cfg.config_dir, self.cfg.build_governor_overlay_text, owner_pid=999999)
        stale.write("game", {}, point_key="45x2")
        other._reconcile_overlays()
        self.assertEqual(other.overlay.read_header("game")["owner"], os.getpid())

    def test_enable_writes_base_overlay_immediately_for_next_launch(self):
        self.assertTrue(self.svc.overlay.exists("game"))
        self.assertEqual(self.header()["owner"], os.getpid())


class LiveAttachTests(RuntimeBase):
    """v0.0.8: the Governor attaches to a game that is already running."""

    def setUp(self):
        super().setUp()
        self.svc.set_enabled("game", False)

    # Inherited check assumes the Governor is on; covered by the other classes.
    test_hud_set_publishes_and_removes_active_config = None

    def test_every_profile_has_a_leased_standby_overlay(self):
        self.svc._reconcile_overlays()
        for name in self.cfg.get_profiles()["profiles"]:
            header = self.svc.overlay.read_header(name)
            self.assertIsNotNone(header, name)
            self.assertEqual(header["owner"], os.getpid())

    def test_standby_overlay_is_exactly_saved(self):
        import tomllib
        saved = tomllib.loads(self.cfg.config_file_path.read_text())
        body = self.svc.overlay.path_for("game").read_text().split("\n", 2)[2]
        self.assertEqual(tomllib.loads(body), saved)

    def test_saved_edit_while_disabled_reaches_standby_overlay(self):
        self.cfg.update_profile_config_fields("game", {"flow_scale": 0.6})
        self.saved_hash = sha(self.cfg.config_file_path)  # user-driven Saved change
        self.step()
        self.assertAlmostEqual(self.overlay_profile()["flow_scale"], 0.6)

    def test_new_profile_gets_standby_overlay(self):
        self.assertTrue(self.cfg.create_profile("fresh", "mako")["success"])
        self.saved_hash = sha(self.cfg.config_file_path)
        self.step()
        self.assertEqual(self.svc.overlay.read_header("fresh")["owner"], os.getpid())

    def test_deleted_profile_overlay_loses_its_lease(self):
        self.assertTrue(self.cfg.create_profile("gone", "mako")["success"])
        self.step()
        self.assertEqual(self.svc.overlay.read_header("gone")["owner"], os.getpid())
        self.assertTrue(self.cfg.delete_profile("gone")["success"])
        self.saved_hash = sha(self.cfg.config_file_path)
        self.step()
        self.assertEqual(self.svc.overlay.read_header("gone")["owner"], 0)

    def test_unchanged_standby_is_not_rewritten(self):
        rev = self.header()["rev"]
        self.svc._standby_overlays_sync(force=True)
        self.svc.set_enabled("game", True)
        self.assertEqual(self.header()["rev"], rev, "a rewrite is a config reload in the running game")

    def test_enable_mid_game_applies_point_without_relaunch(self):
        # Game was launched while the Governor was off: its launch already read the standby overlay.
        self.step()
        self.svc.set_enabled("game", True)
        self.feed(20, 48, 96)
        st = self.step()
        self.assertNotEqual(st.get("reason"), "relaunch-required-for-governor-overlay")
        self.assertTrue(self.svc.power.state.owned)

    def test_hidden_hud_only_for_governor_or_hud_users(self):
        from gfg_plugin.governor_hud import active_config_path
        active = active_config_path(self.cfg.config_dir)
        self.assertFalse(active.exists(), "no Governor, no HUD: MangoHud must not load in games")
        self.svc.set_enabled("game", True)
        self.assertIn("no_display=1", active.read_text())
        self.svc.set_enabled("game", False)
        self.assertFalse(active.exists())
        self.svc.set_hud("game", True)
        self.svc.set_hud("game", False)
        self.assertFalse(active.exists())

    def test_game_launched_right_after_saved_edit_reads_new_overlay(self):
        # No loop iteration in between: the Saved write itself refreshed the standby overlay.
        self.cfg.update_profile_config_fields("game", {"flow_scale": 0.6})
        self.saved_hash = sha(self.cfg.config_file_path)
        self.assertAlmostEqual(self.overlay_profile()["flow_scale"], 0.6)

    def test_plugin_stop_drops_every_lease(self):
        self.assertTrue(self.cfg.create_profile("other2", "mako")["success"])
        self.saved_hash = sha(self.cfg.config_file_path)
        self.step()
        asyncio.run(self.svc.stop())
        for name in self.cfg.get_profiles()["profiles"]:
            header = self.svc.overlay.read_header(name)
            if header is not None:
                self.assertEqual(header["owner"], 0, name)


class BudgetRuntimeTests(RuntimeBase):
    """Default v0.0.6 engine: lowest watts first, renderer-confirmed points."""

    def setUp(self):
        super().setUp()
        self.svc.DEFAULT_MODE = "budget"
        power = self.svc.power
        power.values.update({"minimum_tdp_w": 3.0, "maximum_tdp_w": 20.0})
        power.ceiling = None
        power.set_ceiling_w = lambda w: setattr(power, "ceiling", w)

    def windows(self, n, real, output):
        st = None
        for _ in range(n):
            self.feed(26, real, output)  # ~15.6 s of samples
            st = self.step(0.1)
        return st

    def test_starts_at_10_watts_and_30x3_then_lowers_power(self):
        self.feed(20, 45, 90)
        st = self.step()
        self.assertEqual(st["mode"], "budget")
        self.assertEqual(self.svc.power.ceiling, 20.0)
        self.assertEqual(self.svc.power.writes, [], "no TDP change before the point is live")
        self.assertEqual(st["request"]["point"], "30x3")
        prof = self.overlay_profile()
        self.assertEqual((prof["multiplier"], prof["base_fps_cap"], prof["adaptive"]), (3, 30, False))
        self.feed(16, 30, 90)
        st = self.step()
        self.assertEqual(st["active_point"]["key"], "30x3")
        self.assertIsNone(st["request"])
        self.assertEqual(self.svc.power.writes, [10.0], "watts follow the confirmed point")
        st = self.windows(2, 30, 90)
        self.assertEqual(self.svc.power.writes[-1], 9.0)
        self.assertEqual(st["budget"]["phase"], "search_down")
        self.assertEqual(st["state"], "OPTIMIZE_POWER")

    def test_host_heat_reaches_the_budget_controller(self):
        self.svc.sensors.sample = lambda force=False: {"temp_c": 84.0, "thermal_headroom_c": 6.0}
        self.feed(20, 45, 90)
        self.step()
        self.feed(16, 30, 90)
        st = self.step()
        self.assertEqual(st["diagnosis"]["thermal"], "hot")
        self.assertEqual(self.svc._budget.thermal, "hot")
        self.assertEqual(st["budget"]["thermal"], "hot")

    def applied_line(self, base, mult, adaptive=1):
        return (H + f"operation=runtime-state-applied role=frame-generation state_revision=99 transition=live "
                f"frame_generation_enabled=1 adaptive={adaptive} target_fps=90 multiplier={mult} base_fps_cap={base} "
                "frame_generation_resources_available=1 generated_frame_capacity=2")

    def test_delivered_deeper_ratio_is_resolved_in_seconds_not_25(self):
        """Field log: 36x2.5 / 33x2.75 requests each waited the full 25 s."""
        self.feed(20, 45, 90)
        self.step()
        self.feed(16, 30, 90)
        self.step()
        self.windows(2, 30, 90)                 # 10 W holds -> 9 W
        self.windows(1, 25, 75)                 # 9 W fails -> back to 10 W, upgrade phase
        self.windows(1, 30, 90)
        st = self.step(0.1)
        self.assertEqual(st["request"]["point"], "33x2.75")
        started = self.t["now"]
        self.svc.observer.consume_line(self.applied_line(33, 3), now=self.t["now"])
        self.feed(16, 30, 90)                   # renderer delivers 90 FPS at 30 real (x3)
        st = self.step()
        self.assertIsNone(st["request"])
        self.assertLess(self.t["now"] - started, 15.0)
        events = [json.loads(l) for l in Path(self.svc.events_path).read_text().splitlines()]
        rejected = [e for e in events if e.get("event") == "operating-point-rejected"]
        self.assertEqual(rejected[-1]["reason"], "delivered-deeper-ratio")
        self.assertEqual(st["budget"]["point"], "30x3")

    def test_no_early_decision_without_a_renderer_application(self):
        self.feed(20, 45, 90)
        self.step()
        self.feed(16, 30, 90)
        self.step()
        self.windows(2, 30, 90)
        self.windows(1, 25, 75)
        self.windows(1, 30, 90)
        st = self.step(0.1)
        self.assertEqual(st["request"]["point"], "33x2.75")
        self.feed(16, 30, 90)                   # no runtime-state-applied: the request may not be live yet
        st = self.step()
        self.assertIsNotNone(st["request"])

    def test_session_summary_is_kept_after_the_game_exits(self):
        self.inspector.info["app_id"] = "292030"
        self.feed(20, 45, 90)
        self.step()
        self.feed(16, 30, 90)
        self.step()
        for _ in range(40):
            self.feed(2, 30, 90)
            st = self.step(1.0)
        self.assertIsNotNone(st["session"])
        self.assertGreaterEqual(st["session"]["minutes"], 0.5)
        self.assertEqual(st["session"]["avg_output_fps"], 90.0)
        self.inspector.info["running"] = False          # game closed
        self.inspector.info.pop("app_id")
        self.svc._launch_polled = -1e9
        st = self.step(6.0)
        self.assertIsNone(st["session"])
        last = st["last_session"]
        self.assertIsNotNone(last)
        self.assertEqual(last["avg_output_fps"], 90.0)
        self.assertEqual(last["profile"], "game")
        self.assertEqual(last["mode"], "budget")
        self.assertEqual(last["app_id"], "292030", "taken at the start: the exit no longer knows it")
        self.assertEqual(last["reference_w"], 12.0, "the user's TDP before GFG, not the Battery ceiling")
        self.assertEqual(st["session_history"], [last])

    def test_turning_gfg_off_mid_game_ends_the_session_then(self):
        self.feed(20, 45, 90)
        self.step()
        self.feed(16, 30, 90)
        self.step()
        for _ in range(40):
            self.feed(2, 30, 90)
            self.step(1.0)
        self.svc.set_enabled("game", False)
        st = self.step(1.0)
        self.assertIsNone(st.get("session"))
        self.assertIsNotNone(st["last_session"])
        self.assertEqual(st["last_session"]["profile"], "game")

    def test_failed_lower_power_restores_and_guard_reacts_after_lock(self):
        self.feed(20, 45, 90)
        self.step()
        self.feed(16, 30, 90)
        self.step()
        self.windows(2, 30, 90)                 # 10 W holds -> 9 W
        self.windows(1, 25, 75)                 # 9 W fails (severe) -> back to 10 W
        self.assertEqual(self.svc.power.writes[-1], 10.0)
        st = self.svc.get_status()
        self.assertEqual(st["budget"]["phase"], "upgrade")
        self.assertEqual(st["request"], None)
        self.windows(1, 30, 90)                 # restored 10 W holds once more
        st = self.step(0.1)                     # upgrade probe requests 33x2.75 (fractional)
        self.assertEqual(st["request"]["point"], "33x2.75")
        self.feed_adaptive(16, 33, 90)
        self.step()
        st = self.windows(1, 30, 82)            # 33 real does not hold -> back to 30x3, locked
        self.assertEqual(st["budget"]["point"], "30x3")
        self.assertEqual(st["budget"]["phase"], "locked")
        self.step(0.1)                          # re-apply 30x3
        self.feed(16, 30, 90)
        st = self.step()
        self.assertEqual(st["active_point"]["key"], "30x3")
        self.windows(1, 30, 90)
        self.assertEqual(self.svc.get_status()["state"], "LOCKED")
        # Heavier scene after LOCKED: watts come at once, not after two windows.
        held = self.svc.power.writes[-1]
        self.svc.power.values["draw_w"] = held          # the heavier scene uses the whole cap
        st = self.windows(1, 27, 81)
        self.assertGreater(self.svc.power.writes[-1], held - 1.0)  # a probe reverted or watts were added
        for _ in range(3):
            self.feed(2, 27, 81)
            st = self.step(0.1)
        self.assertEqual(st["reason"], "fast-raise:starved")
        self.assertGreater(self.svc.power.writes[-1], held)

    def test_external_tdp_change_pauses_then_reclaims(self):
        self.feed(20, 45, 90)
        self.step()
        self.feed(16, 30, 90)
        self.step()
        self.svc.power.verify_ownership = lambda: {**self.svc.power.status(), "external_change": True}
        def lose():
            self.svc.power.state.owned = False
            return {**self.svc.power.status(), "external_change": True}
        self.svc.power.verify_ownership = lose
        st = self.windows(1, 30, 90)
        self.assertEqual(st["reason"], "external-tdp-change")
        writes = len(self.svc.power.writes)
        self.svc.power.verify_ownership = lambda: self.svc.power.status()
        self.step(self.svc.EXTERNAL_RECLAIM_SECONDS + 1)
        self.feed(20, 30, 90)
        self.step(0.1)
        self.assertTrue(self.svc.power.state.owned)
        self.assertGreater(len(self.svc.power.writes), writes)

    def test_telemetry_pause_restores_caps_and_target_is_rewritten_after(self):
        self.feed(20, 45, 90)
        self.step()
        self.feed(16, 30, 90)
        self.step()
        self.windows(2, 30, 90)                 # 9 W
        self.assertEqual(self.svc.power.writes[-1], 9.0)
        st = self.step(5.0)                     # loading screen: no FPS -> caps restored
        self.assertEqual(st["state"], "PAUSED")
        self.assertFalse(self.svc.power.state.owned)
        writes = len(self.svc.power.writes)
        self.feed(20, 30, 90)
        self.step(0.1)
        self.assertTrue(self.svc.power.state.owned)
        self.assertEqual(self.svc.power.writes[writes:], [9.0])

    def test_draw_far_above_the_cap_is_reported_as_an_ignored_cap(self):
        self.feed(20, 45, 90)
        self.step()
        self.feed(16, 30, 90)
        self.step()
        self.svc.power.values["draw_w"] = 17.5          # SMU limit raised elsewhere
        st = self.windows(1, 30, 90)
        self.assertFalse(st["budget"]["cap_ignored"])   # one window is not enough
        st = self.windows(1, 30, 90)
        self.assertTrue(st["budget"]["cap_ignored"])
        self.assertEqual(st["power_feedback"]["draw_w"], 17.5)
        self.svc.power.values["draw_w"] = 9.0
        st = self.windows(1, 30, 90)
        self.assertFalse(st["budget"]["cap_ignored"])

    def test_leaving_a_menu_gets_the_working_watts_back_within_seconds(self):
        self.feed(20, 45, 90)
        self.step()
        self.svc.power.values["draw_w"] = 9.5       # the game uses its cap
        self.windows(3, 30, 90)                     # 10 W holds, then 9 W holds ...
        work = self.svc._budget._work_tdp(self.t["now"])
        self.assertIsNotNone(work)
        b = self.svc._budget                         # ... and a long pause menu walked it down to 6 W
        b.tdp, b.probe, b.phase = 6.0, None, "locked"
        self.step(0.1)
        self.assertEqual(self.svc.power.writes[-1], 6.0)
        self.svc.power.values["draw_w"] = 6.0       # the game is back and the cap binds
        for _ in range(3):
            self.feed(2, 12, 36)                    # 12 real: looks like a loading screen
            st = self.step(0.1)
        self.assertEqual(st["reason"], "fast-raise:starved")
        self.assertEqual(self.svc.power.writes[-1], work)

    def test_loading_screen_without_binding_draw_does_not_raise(self):
        self.feed(20, 45, 90)
        self.step()
        self.windows(2, 30, 90)
        tdp = self.svc.power.writes[-1]
        self.svc.power.values["draw_w"] = 3.0       # CPU idle-ish, far under the cap
        for _ in range(4):
            self.feed(2, 12, 36)
            self.step(0.1)
        self.assertEqual(self.svc.power.writes[-1], tdp)

    def test_mode_switch_to_quality_releases_budget_point(self):
        self.feed(20, 45, 90)
        self.step()
        self.assertTrue(self.svc.set_mode("game", "quality")["success"])
        self.assertFalse(self.svc.set_mode("game", "turbo")["success"])
        st = self.step()
        self.assertEqual(st["reason"], "governor-mode-changed")
        self.assertIsNone(st["budget"])
        self.assertFalse(self.svc.power.state.owned)


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


class PointStateResetTests(RuntimeBase):
    """Audit 1.0.7: per-point state that survived a new game, mode or display change."""

    def test_release_clears_exhaustion_reclaims_and_power_feedback(self):
        self.svc._exhausted = True
        self.svc._reclaims, self.svc._external_at = 3, 12.0
        self.svc._status["power_feedback"] = {"cap_w": 7.0, "draw_w": 7.1}
        asyncio.run(self.svc._release_point("game", "new-game-session"))
        self.assertFalse(self.svc._exhausted)
        self.assertEqual((self.svc._reclaims, self.svc._external_at), (0, None))
        self.assertNotIn("power_feedback", self.svc._status)

    def test_stale_power_feedback_does_not_fake_a_power_bottleneck(self):
        self.svc.sensors.sample = lambda force=False: {"gpu_busy_pct": 40.0, "cpu_top_core_pct": 98.0}
        self.svc._budget = None
        self.svc._status["power_feedback"] = {"cap_w": 7.0, "draw_w": 7.1}   # left by Battery mode
        self.svc._update_sensors()
        self.assertEqual(self.svc._status["diagnosis"]["bottleneck"], "cpu")
