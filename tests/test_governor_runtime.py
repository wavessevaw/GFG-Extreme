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
from unittest.mock import patch
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
from gfg_plugin.cpu_freq import CpuFreqActuator  # noqa: E402
from gfg_plugin import power_split  # noqa: E402


def ps_probe_s():
    return power_split.PROBE_S

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
        # a cpufreq tree of its own: never the machine's (power split, 1.5)
        self.cpufreq = Path(HOME) / "cpufreq"
        for i in range(2):
            d = self.cpufreq / f"policy{i}"
            d.mkdir(parents=True)
            (d / "cpuinfo_max_freq").write_text("3500000\n")
            (d / "cpuinfo_min_freq").write_text("1400000\n")
            (d / "scaling_max_freq").write_text("3500000\n")
        self.svc.cpu = CpuFreqActuator(root=self.cpufreq, helper=lambda: None, access=lambda p, m: True,
                                       marker=Path(HOME) / "cpu-cap.json")
        self.svc.DEFAULT_MODE = "quality"  # the v0.0.2 ladder; budget mode has its own tests
        self.svc.PREDICTIVE_SKIP = False
        self.svc.hud.MIN_REWRITE_S = 0.0  # MangoHud rewrite rate limit has its own tests  # these tests walk the full ladder; see PredictiveStartTests
        self.t = {"now": 100.0}
        self.svc.observer.time_fn = lambda: self.t["now"]
        self.svc._last_display_poll = -1e9
        self.assertIsNone(self.svc.set_enabled("game", True).get("overlay_error"))

    def tearDown(self):
        self.assertEqual(sha(self.cfg.config_file_path), self.saved_hash, "Saved config was modified")

    def test_stale_focus_lost_cannot_pin_frame_os_in_rest(self):
        self.svc.observer.game_focused = False
        self.svc.observer.game_focused_at = self.t["now"] - 7.0
        self.assertIsNone(self.svc._trusted_game_focus())
        self.svc.observer.game_focused_at = self.t["now"] - 1.0
        self.assertIs(self.svc._trusted_game_focus(), False)
        self.svc.observer.game_focused = True
        self.assertIs(self.svc._trusted_game_focus(), True)

    def test_default_ring_marker_is_staged_without_prior_governor_settings(self):
        # A ConfigService profile need not have any saved Governor or HUD preferences.
        self.svc._settings = {"schema": 1, "profiles": {}}
        self.assertEqual(self.svc.hud_settings("game")["position"], "bottom-left")
        self.assertTrue(self.svc.hud_settings("game")["enabled"])
        self.svc._sync_frame_os_marker()
        self.assertTrue(self.svc.ring_hud_marker_path.exists())

    def test_ring_hud_falls_back_to_text_until_the_layer_reports(self):
        import time as _t
        from gfg_plugin import hud_rings
        self.svc.ring_hud_path = self.cfg.config_dir / "hud.raw"
        self.svc.ring_hud_extent = self.cfg.config_dir / "hud.extent"
        self.svc.set_hud("game", True, "standard", "top-left")
        self.assertTrue(self.svc.ring_hud_marker_path.exists(), "the launcher adds the HUD layer")
        self.step()
        self.assertFalse(self.svc.ring_hud_path.exists(), "no layer report yet: text line, no bitmap")
        self.svc._launch = {"running": True, "launch_key": [1, 2, _t.time() - 30]}
        self.svc.ring_hud_extent.write_text("1280 800 0\n")   # HDR / unsupported swapchain: passed through
        self.svc._sync_hud("game")
        self.assertFalse(self.svc.ring_hud_path.exists(), "layer draws nothing here: keep the text line")
        self.svc.ring_hud_extent.write_text("1280 800 1\n")
        self.svc._sync_hud("game")
        raw = self.svc.ring_hud_path.read_bytes()
        magic, version, w, h, corner, margin, seq, _ = hud_rings.HEADER.unpack_from(raw)
        self.assertEqual((magic, version, corner), (hud_rings.MAGIC, 1, 0))
        self.assertEqual(len(raw), hud_rings.HEADER.size + w * h * 4)
        self.svc._sync_hud("game")                 # within 1 s: not redrawn
        self.assertEqual(hud_rings.HEADER.unpack_from(self.svc.ring_hud_path.read_bytes())[6], seq)
        self.svc.set_hud("game", True, None, None, "text")
        self.svc._sync_hud("game")
        self.assertEqual(hud_rings.HEADER.unpack_from(self.svc.ring_hud_path.read_bytes())[2], 0, "rings cleared")
        self.assertFalse(self.svc.ring_hud_marker_path.exists())

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
        self.assertEqual(self.svc.get_status("game")["hud"],
                         {"enabled": True, "preset": "detailed", "position": "top-right", "style": "rings"})
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
        self.assertFalse(self.svc._is_idle(), "new installs keep Rings enabled even with Governor off")
        self.svc.set_hud("game", False)
        self.assertTrue(self.svc._is_idle())
        self.svc.set_hud("game", True)
        self.assertFalse(self.svc._is_idle())          # HUD status needs the loop
        self.svc.set_hud("game", False)
        self.assertTrue(self.svc._is_idle())

    def test_loop_wakes_immediately_when_poked_while_idle(self):
        async def scenario():
            self.svc.set_enabled("game", False)
            self.svc.set_hud("game", False)
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
    def test_expired_steam_menu_focus_does_not_freeze_governor(self):
        self.feed(12, 30, 90)
        self.svc.observer.game_focused = False
        self.svc.observer.game_focused_at = self.t["now"] - 8.0
        st = self.step()
        self.assertNotEqual(st.get("reason"), "steam-menu-open")
        self.assertIsNone(self.svc._menu_since)

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

    def test_panel_refresh_rate_caps_the_target_and_invalidates_point(self):
        self.display.read_current_refresh_hz = lambda: None          # not readable: nothing changes
        self.apply_45x2()
        self.assertEqual(self.svc.get_status()["target_output_fps"], 90)
        self.display.read_current_refresh_hz = lambda: 90
        self.svc._last_display_poll = -1e9
        st = self.step()
        self.assertEqual(st["target_output_fps"], 90)
        self.assertIsNotNone(st["active_point"])
        self.display.read_current_refresh_hz = lambda: 60          # the player set the panel to 60 Hz
        self.svc._last_display_poll = -1e9
        st = self.step()
        self.assertEqual(st["target_output_fps"], 60)
        self.assertEqual(st["device"]["target_reason"], "panel-running-60hz")
        self.assertEqual(st["reason"], "display-mode-changed")
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

    def test_hud_only_default_rings_keep_live_fps_and_target(self):
        """Default overlay cannot depend on the power Governor being enabled."""
        from gfg_plugin import hud_rings
        self.assertFalse(self.svc._profile_enabled("game"))
        self.assertTrue(self.svc.hud_settings("game")["enabled"])
        self.feed(12, 30, 90)
        st = self.step()
        self.assertFalse(st["enabled"], "passive telemetry must not enable Governor")
        self.assertEqual(st["telemetry"]["snapshot"]["latest"]["output_fps"], 90)
        self.assertEqual(st["target_output_fps"], 90, "OLED ring uses display refresh")
        self.assertTrue(self.svc._launch.get("running"), "HUD-only still probes the active game")
        self.assertFalse(self.svc.power.state.owned)
        with patch.object(hud_rings, "write_overlay", return_value=True) as writer:
            self.svc._ring_hud_due = 0
            self.svc._ring_hud_key = None
            self.assertTrue(self.svc._publish_ring_hud(st, self.svc.hud_settings("game")))
        picture = writer.call_args.args[0]
        self.assertEqual((picture["fps"], picture["real"], picture["target"]), (90, 30, 90))

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
        self.assertEqual(self.svc.hud_settings("game"),
                         {"enabled": True, "preset": "standard", "position": "bottom-left", "style": "rings"})
        self.svc._sync_hud_presence()
        self.assertIn("no_display=1", active.read_text(), "default HUD preloaded for first launch")
        self.svc.set_hud("game", False)
        self.svc.set_enabled("game", False)
        self.assertFalse(active.exists(), "user-disabled HUD stays disabled")
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

    def cpu_khz(self):
        return int((self.cpufreq / "policy0" / "scaling_max_freq").read_text())

    def gpu_bound_play(self, seconds, top=30.0, until_capped=False):
        self.svc.sensors.sample = lambda force=False: {"gpu_busy_pct": 97.0, "cpu_top_core_pct": top,
                                                       "gpu_clock_mhz": 1200.0}
        st = None
        end = self.t["now"] + seconds
        self.lowest_khz = 3_500_000
        while self.t["now"] < end:
            self.feed(2, 30, 90)
            st = self.step(1.0)
            self.lowest_khz = min(self.lowest_khz, self.cpu_khz())
            if until_capped and self.cpu_khz() < 3_500_000:
                break
        return st

    def test_power_split_caps_the_cpu_in_a_gpu_bound_game_and_gives_it_back(self):
        self.feed(20, 45, 90)
        self.step()
        self.feed(16, 30, 90)
        self.step()
        st = self.gpu_bound_play(90, until_capped=True)
        self.assertLess(self.cpu_khz(), 3_500_000, "GPU-bound with CPU headroom: the CPU clock is capped")
        self.assertEqual(self.cpu_khz(), int((self.cpufreq / "policy1" / "scaling_max_freq").read_text()))
        self.assertIn(st["power_split"]["phase"], ("probe", "hold"))
        events = [json.loads(l) for l in Path(self.svc.events_path).read_text().splitlines()]
        steps = [e for e in events if e.get("event") == "power-split"]
        self.assertTrue(steps and steps[0]["reason"] == "step-down")
        self.gpu_bound_play(ps_probe_s() + 3)          # the probe holds: the level is remembered
        game = self.svc._split_key[0]
        self.assertGreater(self.svc._settings["power_split_games"][game]["level"], 0, "remembered per game")
        # the point goes (game exit, mode change): the user's clock is back at once
        asyncio.run(self.svc._release_point("game", "test"))
        self.assertEqual(self.cpu_khz(), 3_500_000)
        self.assertFalse(Path(HOME, "cpu-cap.json").exists())

    def test_power_split_lifts_the_cap_when_real_frames_drop(self):
        self.feed(20, 45, 90)
        self.step()
        self.feed(16, 30, 90)
        self.step()
        self.gpu_bound_play(90, until_capped=True)
        self.assertLess(self.cpu_khz(), 3_500_000)
        self.feed(5, 24, 72)
        st = self.step(1.0)
        self.assertEqual(self.cpu_khz(), 3_500_000, "real frames come first")
        self.assertEqual(st["power_split"]["reason"], "real-frames-short")

    def test_power_split_off_switch_and_unload(self):
        self.feed(20, 45, 90)
        self.step()
        self.feed(16, 30, 90)
        self.step()
        self.gpu_bound_play(90, until_capped=True)
        self.assertLess(self.cpu_khz(), 3_500_000)
        self.assertTrue(self.svc.set_power_split(False)["success"])
        self.gpu_bound_play(3)
        self.assertEqual(self.cpu_khz(), 3_500_000)
        self.svc.set_power_split(True)
        self.gpu_bound_play(90, until_capped=True)
        self.assertLess(self.cpu_khz(), 3_500_000)
        asyncio.run(self.svc.stop())
        self.assertEqual(self.cpu_khz(), 3_500_000, "unload gives the clock back")

    def test_power_split_never_caps_a_busy_cpu(self):
        self.feed(20, 45, 90)
        self.step()
        self.feed(16, 30, 90)
        self.step()
        self.gpu_bound_play(120, top=78.0)
        self.assertEqual(self.lowest_khz, 3_500_000)

    def capacity_report(self, frames):
        self.svc.observer.consume_line(
            H + "operation=runtime-state-applied role=frame-generation "
            + ("frame_generation_resources_available=0 generated_frame_capacity=0"
               if frames == 0 else
               f"frame_generation_resources_available=1 generated_frame_capacity={frames}"),
            now=self.t["now"],
        )

    def test_zero_generated_slots_pause_without_repeated_power_claims(self):
        # x3 was requested, but a swapchain transition has zero FG resources.
        self.feed(20, 45, 90)
        st = self.step()
        self.assertEqual(st["request"]["point"], "30x3")
        self.capacity_report(0)
        st = self.step(0.1)
        self.assertEqual((st["state"], st["reason"]),
                         ("OBSERVE_ONLY", "renderer-capacity-unavailable"))
        self.assertIsNone(self.svc._request)
        self.assertIsNone(self.svc._budget)
        self.assertFalse(self.svc.power.state.owned)
        self.assertEqual(self.svc.power.writes, [])
        self.assertEqual(self.svc.game_models.failures(self.svc._game_key("game", 90)), {})
        header = self.header()
        for _ in range(6):
            st = self.step(0.1)
            self.assertEqual(st["reason"], "renderer-capacity-unavailable")
        self.assertEqual(self.header(), header, "no repeated overlay rewrites")
        self.assertEqual(self.svc.power.writes, [], "no hidden cap chase")
        self.assertFalse(self.svc.power.state.owned)

        self.capacity_report(2)  # x3 becomes possible again
        self.feed(20, 45, 90)
        st = self.step(0.1)
        self.assertEqual(st["reason"], "renderer-capacity-recovering")
        st = self.step(0.1)
        self.assertEqual(st["reason"], "renderer-capacity-recovering")
        self.feed(5, 45, 90, dt=0.5)
        st = self.step(0.1)
        self.assertEqual(st["request"]["point"], "30x3")
        self.assertEqual(self.svc._budget.request_failures, 0)
        self.assertEqual(self.svc._budget.rejected, {})
        self.feed(16, 30, 90)
        st = self.step()
        self.assertEqual(st["active_point"]["key"], "30x3")

    def test_capacity_waits_for_successful_saved_overlay_restore(self):
        """A failed restore must never be reported as safely observe-only."""
        self.feed(20, 45, 90)
        self.step()
        self.feed(16, 30, 90)
        self.step()
        self.assertEqual(self.svc._point["key"], "30x3")
        original_write = self.svc._write_overlay_sync
        original_restore = self.svc._restore_overlay_sync

        def fail_write(*args, **kwargs):
            raise OSError("synthetic overlay storage failure")

        try:
            self.svc._write_overlay_sync = fail_write
            self.svc._restore_overlay_sync = lambda *args, **kwargs: "synthetic restore failure"
            self.capacity_report(0)
            state = self.step(0.1)
            self.assertEqual((state["state"], state["reason"]), ("PAUSED", "overlay-restore-failed"))
            self.assertTrue(self.svc._capacity_paused)
            self.assertIn("game", self.svc._restore_pending)
            self.assertFalse(self.svc.power.state.owned, "TDP should be restored even if overlay failed")

            # A positive capacity report must not start the recovery gate or
            # send a fresh FG request while Saved overlay is not restored.
            self.capacity_report(2)
            self.feed(5, 45, 90, dt=0.5)
            state = self.step(0.1)
            self.assertEqual((state["state"], state["reason"]), ("PAUSED", "overlay-restore-failed"))
            self.assertIsNone(self.svc._capacity_restore_at)
            self.assertIsNone(self.svc._request)

            self.svc._write_overlay_sync = original_write
            self.svc._restore_overlay_sync = original_restore
            state = self.step(0.1)
            self.assertNotIn("game", self.svc._restore_pending)
            self.assertEqual(state["reason"], "renderer-capacity-recovering")
            self.assertIsNone(self.svc._request)
            self.feed(5, 45, 90, dt=0.5)
            state = self.step(0.1)
            self.assertEqual(state["request"]["point"], "30x3")
        finally:
            self.svc._write_overlay_sync = original_write
            self.svc._restore_overlay_sync = original_restore

    def test_zero_slot_bounce_restarts_two_second_recovery_gate(self):
        self.feed(20, 45, 90)
        self.step()
        self.capacity_report(0)
        self.step(0.1)
        self.assertTrue(self.svc._capacity_paused)
        self.capacity_report(2)
        self.feed(6, 45, 90, dt=0.5)
        self.step(0.1)
        self.assertIsNotNone(self.svc._capacity_restore_at)
        self.capacity_report(0)  # no slots AGAIN, before the gate closes
        st = self.step(0.1)
        self.assertEqual(st["reason"], "renderer-capacity-unavailable")
        self.assertIsNone(self.svc._capacity_restore_at)
        self.capacity_report(2)
        self.feed(4, 45, 90, dt=0.5)
        st = self.step(0.1)
        self.assertEqual(st["reason"], "renderer-capacity-recovering")
        self.assertTrue(self.svc._capacity_paused)
        self.feed(5, 45, 90, dt=0.5)
        st = self.step(0.1)
        self.assertEqual(st["request"]["point"], "30x3")

    def test_live_x3_to_x2_to_x3_recovers_without_false_blacklist(self):
        self.feed(20, 45, 90)
        self.step()
        self.feed(16, 30, 90)
        self.step()
        self.assertEqual(self.svc._point["key"], "30x3")
        budget = self.svc._budget

        self.capacity_report(1)  # one generated slot: maximum x2
        self.feed(12, 45, 90)
        st = self.step(0.1)
        self.assertEqual(st["request"]["point"], "45x2")
        self.assertEqual(budget.point.key, "45x2")
        self.assertEqual(budget.request_failures, 0)
        self.assertFalse(budget.rejected)
        self.feed(16, 45, 90)
        st = self.step()
        self.assertEqual(st["active_point"]["key"], "45x2")

        self.capacity_report(2)
        self.feed(5, 45, 90, dt=0.5)
        self.step(0.1)  # first evidence of recovered x3 capacity
        self.feed(5, 45, 90, dt=0.5)
        st = self.step(0.1)
        self.assertEqual(st["request"]["point"], "30x3")
        self.assertEqual(budget.request_failures, 0)
        self.assertFalse(budget.rejected)
        self.feed(16, 30, 90)
        st = self.step()
        self.assertEqual(st["active_point"]["key"], "30x3")

    def test_pending_request_cancelled_without_hard_failure_on_resource_change(self):
        self.feed(20, 45, 90)
        st = self.step()
        self.assertEqual(st["request"]["point"], "30x3")
        self.capacity_report(1)
        st = self.step(0.1)
        self.assertEqual(st["reason"], "renderer-capacity-request-cancelled")
        self.assertIsNone(self.svc._request)
        self.assertIsNone(self.svc._budget)
        self.assertEqual(self.svc.game_models.failures(self.svc._game_key("game", 90)), {})
        self.feed(20, 45, 90)
        st = self.step(0.1)
        self.assertEqual(st["request"]["point"], "45x2")
        self.assertEqual(self.svc._budget.request_failures, 0)
        self.assertEqual(self.svc._budget.rejected, {})

    def test_fast_tdp_rescue_never_double_counts_a_cached_fps_window(self):
        """One renderer sample batch is one check, not two just because the UI polls twice."""
        self.feed(20, 45, 90)
        self.step()
        self.feed(16, 30, 90)
        self.step()
        budget = self.svc._budget
        self.assertIsNotNone(budget)
        self.assertEqual(self.svc._point["key"], "30x3")
        self.step(0.1)  # initialize the new point's fresh-evidence cursor
        baseline = budget.tdp
        self.svc.power.values["draw_w"] = baseline
        self.feed(4, 20, 60, dt=0.45)
        self.step(0.1)
        self.assertEqual(budget.starved_checks, 1)
        self.assertEqual(budget.tdp, baseline)
        # No new renderer sample here. Cached median cannot trigger a fast raise.
        self.step(0.1)
        self.assertEqual(budget.starved_checks, 0)
        self.assertEqual(budget.tdp, baseline)
        self.feed(4, 20, 60, dt=0.45)
        self.step(0.1)
        self.assertEqual(budget.starved_checks, 1)
        self.assertEqual(budget.tdp, baseline)
        self.feed(4, 20, 60, dt=0.45)
        self.step(0.1)
        self.assertGreater(budget.tdp, baseline, "two independent low-FPS batches justify watts")

    def test_game_change_discards_fast_fps_and_act_evidence(self):
        # Even if the new game selects the same 30x3 operating point, its
        # renderer samples and Act grace window belong to a different session.
        self.feed(20, 45, 90)
        self.step()
        self.feed(16, 30, 90)
        self.step()
        self.assertEqual(self.svc._point["key"], "30x3")
        self.svc._fast_point_key = "30x3"
        self.svc._fast_last_sample_seq = 999999
        self.svc._injection_started_at = self.t["now"] - 50
        self.inspector.info["launch_key"] = [9, 9, 9]
        self.svc._launch_polled = -1e9
        state = self.step()
        self.assertEqual(state["reason"], "new-game-session")
        self.assertIsNone(self.svc._fast_point_key)
        self.assertLess(self.svc._fast_last_sample_seq, 999999)
        self.assertIsNone(self.svc._injection_started_at)

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

    # -- review 1.1.x backlog
    def test_mode_switch_keeps_the_floor_back_off(self):
        self.inspector.info["app_id"] = "292030"
        self.feed(20, 45, 90)
        self.step()
        self.feed(16, 30, 90)
        self.step()
        self.windows(2, 30, 90)                 # 10 W holds -> 9 W
        self.windows(1, 25, 75)                 # 9 W fails -> back to 10 W
        self.step(0.1)                          # drained into game memory
        stored = self.svc.game_models.floor_failures(self.svc._floor_key("game", 90))
        self.assertEqual(stored["30x3"][0], 9.0)
        self.assertEqual(stored["30x3"][2], 1)
        self.assertTrue(self.svc.set_mode("game", "balanced")["success"])
        self.step()
        self.feed(20, 45, 90)
        self.step()
        b = self.svc._budget
        self.assertIsNotNone(b)
        self.assertEqual(b.flavor, "balanced")
        idx = next(i for i, p in enumerate(b.points) if p.key == "30x3")
        tdp, when, count = b.floor_failures[idx]
        self.assertEqual((tdp, count), (9.0, 1))
        self.assertLessEqual(when, self.t["now"], "the original back-off keeps running")

    def test_hot_states_are_not_remembered(self):
        svc = self.svc
        svc._applied_tdp = 9.0
        point = types.SimpleNamespace(key="30x3", degraded=False)
        budget = types.SimpleNamespace(phase="locked", recover=None, cap_ignored=False, exhausted=False,
                                       verifying=None, locked_since=0.0, tdp_control=True, tdp=9.0,
                                       heat_limited=True)
        key = svc._game_key("game", 90)
        svc._remember_if_held("game", 90, budget, point, 1000.0)
        self.assertIsNone(svc.game_models.get(key), "heat held quality back: not what the game needs")
        budget.heat_limited = False
        svc._status["diagnosis"] = {"thermal": "heating"}
        svc._remember_if_held("game", 90, budget, point, 1000.0)
        self.assertIsNone(svc.game_models.get(key))
        svc._status["diagnosis"] = {"thermal": "ok"}
        svc._remember_if_held("game", 90, budget, point, 1000.0)
        self.assertEqual(svc.game_models.get(key)["point"], "30x3")

    def test_guard_hold_without_power_shortage_is_logged(self):
        self.feed(20, 45, 90)
        self.step()
        self.feed(16, 30, 90)
        self.step()
        b = self.svc._budget
        b.phase, b.probe, b.locked_since = "locked", None, self.t["now"]
        self.svc.power.values["draw_w"] = 4.0   # far under the 10 W cap: not power-bound
        self.windows(2, 27, 81)
        self.assertTrue(b.last_reason.startswith("guard-not-power-bound"))
        events = [json.loads(l) for l in Path(self.svc.events_path).read_text().splitlines()]
        held = [e for e in events if e.get("event") == "budget-guard-not-power-bound"]
        self.assertEqual(len(held), 1)
        self.assertEqual((held[0]["draw_w"], held[0]["cap_w"]), (4.0, 10.0))
        self.assertTrue(held[0]["verdict"])
        self.windows(2, 27, 81)                 # in the guard every window holds again, same reason
        events = [json.loads(l) for l in Path(self.svc.events_path).read_text().splitlines()]
        held = [e for e in events if e.get("event") == "budget-guard-not-power-bound"]
        self.assertEqual(len(held), b.not_power_bound_holds)
        self.assertEqual(held[-1]["count"], 3)

    def test_mixed_mode_session_is_filed_as_mixed(self):
        self.feed(20, 45, 90)
        self.step()
        self.feed(16, 30, 90)
        self.step()
        for _ in range(40):
            self.feed(2, 30, 90)
            self.step(1.0)
        self.svc.set_mode("game", "balanced")
        for _ in range(40):
            self.feed(2, 45, 90)
            self.step(1.0)
        self.inspector.info["running"] = False
        self.svc._launch_polled = -1e9
        last = self.step(6.0)["last_session"]
        self.assertEqual(last["mode"], "mixed")
        self.assertEqual(set(last["modes"]), {"budget", "balanced"})

    def test_forget_game_model_resets_this_game_only(self):
        svc = self.svc
        svc._settings["last_session"] = {"profile": "game", "app_id": "292030"}
        from gfg_plugin.game_model import context_key, floor_key
        mine = context_key("game", 90, "budget", "292030")
        other = context_key("other", 90, "budget", "570")
        svc.game_models.record(mine, "30x3", 9.0)
        svc.game_models.record(context_key("game", 60, "balanced", "292030"), "30x2", 12.0)
        svc.game_models.record_floor_failure(floor_key("game", 90, "292030"), "30x3", 8.0)
        svc.game_models.record(other, "45x2", 11.0)
        r = svc.forget_game_model("game")
        self.assertTrue(r["success"])
        self.assertEqual((r["game"], r["forgotten"]), ("app:292030", 3))
        self.assertIsNone(svc.game_models.get(mine))
        self.assertIsNotNone(svc.game_models.get(other))
        self.assertFalse(svc.forget_game_model("")["success"])

    def test_forget_game_model_forgets_the_power_split_too(self):
        svc = self.svc
        svc._settings["last_session"] = {"profile": "game", "app_id": "292030"}
        svc._settings["power_split_games"] = {"app:292030": {"level": 3, "pairs": [5.0]}, "app:570": {"level": 1}}
        r = svc.forget_game_model("game")
        self.assertEqual(r["forgotten"], 1)
        self.assertEqual(list(svc._settings["power_split_games"]), ["app:570"])

    def test_forget_game_model_names_the_game_or_refuses(self):
        svc = self.svc
        from gfg_plugin.game_model import context_key
        svc._settings.pop("last_session", None)
        self.assertIsNone(svc.game_model_target("Default"))
        r = svc.forget_game_model("Default")
        self.assertEqual((r["success"], r["error"]), (False, "no-game-identified"), "never a silent success")
        # The shared Default profile: the last game played under it, named by AppID before the reset.
        svc._settings["last_session"] = {"profile": "Default", "app_id": "570"}
        self.assertEqual(svc.game_model_target("Default"), {"profile": "Default", "app_id": "570", "game": "app:570"})
        self.assertIsNone(svc.game_model_target("other"), "another profile's last game is not this one's")
        # No AppID: only what was stored under the profile itself, and only when there is something.
        svc.game_models.record(context_key("other", 90, "budget"), "30x3", 9.0)
        self.assertEqual(svc.game_model_target("other"), {"profile": "other", "app_id": "", "game": "other"})
        self.assertEqual(svc.forget_game_model("other")["forgotten"], 1)
        self.assertIsNone(svc.game_model_target("other"))

    def test_forget_game_model_runs_on_the_event_loop(self):
        import asyncio
        from unittest import mock
        from gfg_plugin import plugin as plugin_module
        fake = mock.Mock()
        fake.governor_service.forget_game_model.return_value = {"success": True}
        with mock.patch.object(asyncio, "to_thread", side_effect=AssertionError("worker thread")):
            r = asyncio.run(plugin_module.Plugin.forget_governor_game_model(fake, "game"))
        self.assertEqual(r, {"success": True})
        fake.governor_service.forget_game_model.assert_called_once_with("game")

    def test_queued_failures_survive_a_mode_switch_and_game_exit(self):
        from gfg_plugin.game_model import context_key, floor_key
        self.inspector.info["app_id"] = "292030"
        for leave in ("mode", "relaunch"):
            self.svc.game_models.forget_game("app:292030")
            self.svc.set_mode("game", "budget")
            self.inspector.info["running"] = True
            self.svc._launch_polled = -1e9
            self.feed(20, 45, 90)
            self.step()
            b = self.svc._budget
            self.assertIsNotNone(b, leave)
            b.new_failures.append(("33x2.75", 10.0))             # queued, not yet drained
            b.new_floor_failures.append(("30x3", 8.0, 1))
            if leave == "mode":
                self.svc.set_mode("game", "quality")
            else:                                                 # the game exits, the next one starts
                self.inspector.info["launch_key"] = [7, 7, 7]
                self.svc._launch_polled = -1e9
            self.step()
            self.assertIsNone(self.svc._budget, leave)
            self.assertIn("33x2.75", self.svc.game_models.failures(context_key("game", 90, "budget", "292030")),
                          f"{leave}: stored under the mode it failed in")
            self.assertIn("30x3", self.svc.game_models.floor_failures(floor_key("game", 90, "292030")), leave)

    def test_forget_game_model_clears_the_live_controller(self):
        self.inspector.info["app_id"] = "292030"
        self.feed(20, 45, 90)
        self.step()
        b = self.svc._budget
        b.known_failures["33x2.75"] = (10.0, 0.0)
        b.floor_failures[b.idx] = (9.0, 0.0, 2)
        self.svc._active_profile = "game"
        r = self.svc.forget_game_model("game")
        self.assertEqual(r["game"], "app:292030")
        self.assertEqual((b.known_failures, b.floor_failures), ({}, {}))

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

    def test_release_clears_exhaustion_and_power_feedback_but_not_reclaims(self):
        self.svc._exhausted = True
        self.svc._reclaims, self.svc._external_at = 3, 12.0
        self.svc._status["power_feedback"] = {"cap_w": 7.0, "draw_w": 7.1}
        asyncio.run(self.svc._release_point("game", "new-game-session"))
        self.assertFalse(self.svc._exhausted)
        # Review 1.0.10: a new game must not restart the fight with an outside TDP tool.
        self.assertEqual((self.svc._reclaims, self.svc._external_at), (3, 12.0))
        self.assertNotIn("power_feedback", self.svc._status)

    def test_stale_power_feedback_does_not_fake_a_power_bottleneck(self):
        self.svc.sensors.sample = lambda force=False: {"gpu_busy_pct": 40.0, "cpu_top_core_pct": 98.0}
        self.svc._budget = None
        self.svc._status["power_feedback"] = {"cap_w": 7.0, "draw_w": 7.1}   # left by Battery mode
        self.svc._update_sensors()
        self.assertEqual(self.svc._status["diagnosis"]["bottleneck"], "cpu")

    def test_tdp_control_is_probed_again_when_it_was_missing_at_start(self):
        power = self.svc.power
        power.state.available = False
        power.discover = lambda: setattr(power.state, "available", True) or power.status()
        self.assertTrue(asyncio.run(self.svc._rediscover_power()))
        power.state.available = False
        self.assertFalse(asyncio.run(self.svc._rediscover_power()), "at most every 30 s")


class FrameOsIntegrationTests(BudgetRuntimeTests):
    """Development feature: off by default, marker for the launcher, TDP offset only in act mode."""

    def test_off_by_default_and_marker_follows_the_mode(self):
        self.assertEqual(self.svc._frame_os_mode("game"), "off")
        self.assertFalse(self.svc.frame_os_marker_path.exists())
        self.assertTrue(self.svc.set_frame_os("game", "observe")["success"])
        self.assertTrue(self.svc.frame_os_marker_path.exists())
        self.assertFalse(self.svc.set_frame_os("game", "turbo")["success"])
        self.svc.set_frame_os("game", "off")
        self.assertFalse(self.svc.frame_os_marker_path.exists())

    def test_turning_frame_os_on_stages_the_bundled_layer(self):
        from gfg_plugin.frame_os import layer_install
        base = self.svc.frame_os_marker_path.parent
        self.svc.frame_os_layer_source = base / "bundle"
        self.svc.frame_os_layer_dir = base / "staged"
        self.svc.set_frame_os("game", "observe")             # a build without the layer
        frame_os = self.svc.get_status("game")["frame_os"]
        self.assertFalse(frame_os["layer_installed"])
        self.assertIn("does not include", frame_os["layer_error"])
        self.svc.frame_os_layer_source.mkdir(parents=True)
        (self.svc.frame_os_layer_source / layer_install.LIBRARY).write_bytes(b"ELF")
        (self.svc.frame_os_layer_source / layer_install.MANIFEST).write_text('{"layer": {"name": "VK_LAYER_GFG_pacer"}}')
        self.svc.frame_os_registry_dir = base / "registry"
        self.svc.set_frame_os("game", "shadow")
        frame_os = self.svc.get_status("game")["frame_os"]
        self.assertTrue(frame_os["layer_installed"])
        self.assertIsNone(frame_os["layer_error"])
        self.assertTrue((base / "registry" / layer_install.REGISTERED_MANIFEST).is_file())

    def test_runner_follows_the_live_budget_point(self):
        self.svc.set_frame_os("game", "observe")
        self.feed(20, 45, 90)
        self.step()
        self.feed(16, 30, 90)
        self.step()
        runner = self.svc.frame_os
        self.assertTrue(runner.enabled)
        self.assertEqual((runner.policy.output_hz, runner.policy.calm_real_hz), (90.0, 30.0))
        self.assertEqual(runner.tdp_offset_w, 0.0, "observe never moves watts")
        self.assertEqual(self.svc.get_status("game")["frame_os"]["mode"], "observe")

    def test_act_requires_explicit_developer_unlock(self):
        with patch.dict(os.environ, {"GFG_FRAME_OS_EXPERIMENTAL_ACT": "0"}):
            refused = self.svc.set_frame_os("game", "act")
            self.assertFalse(refused["success"])
            self.assertEqual(self.svc._frame_os_mode("game"), "off")
            self.assertFalse(self.svc.frame_os_marker_path.exists())
            self.assertFalse(self.svc.get_status("game")["frame_os"]["act_unlocked"])

            # A prior build could have persisted Act; never implicitly apply it.
            self.svc._settings.setdefault("profiles", {}).setdefault("game", {})["frame_os"] = "act"
            self.assertEqual(self.svc._frame_os_mode("game"), "off")
            self.svc._sync_frame_os_marker()
            self.assertFalse(self.svc.frame_os_marker_path.exists())

    def test_act_unlock_setting_persists_without_env(self):
        with patch.dict(os.environ, {"GFG_FRAME_OS_EXPERIMENTAL_ACT": "0"}):
            self.assertFalse(self.svc.set_frame_os("game", "act")["success"])
            self.assertTrue(self.svc.set_frame_os_act_unlock(True)["act_unlocked"])
            self.assertTrue(self.svc.set_frame_os("game", "act")["success"])
            self.assertTrue(self.svc.frame_os_marker_path.exists())
            self.assertFalse(self.svc.set_frame_os_act_unlock(False)["act_unlocked"])
            self.assertEqual(self.svc._frame_os_mode("game"), "observe", "locking means back to measuring")
            self.svc.set_frame_os_act_unlock(True)
            self.assertEqual(self.svc._frame_os_mode("game"), "observe", "unlocking never re-arms Act silently")

    def test_ab_check_is_on_by_default_and_persists_off(self):
        self.assertTrue(self.svc.get_status("game")["frame_os"]["ab"])
        self.assertTrue(self.svc.frame_os.proof.enabled)
        self.assertFalse(self.svc.set_frame_os_ab(False)["ab"])
        self.assertFalse(self.svc.frame_os.proof.enabled)
        self.assertFalse(self.svc.get_status("game")["frame_os"]["ab"])
        self.assertIs(self.svc._settings["frame_os_ab"], False)
        self.svc.set_frame_os_ab(True)

    def _act_live_point(self):
        self.svc.set_frame_os_act_unlock(True)
        self.assertTrue(self.svc.set_frame_os("game", "act")["success"])
        self.feed(20, 45, 90)
        self.step()
        self.feed(16, 30, 90)
        self.step()
        self.assertEqual(self.svc._point["key"], "30x3")

    def test_frame_os_remembers_ab_results_per_game(self):
        self.inspector.info.update(app_id="4242", launch_key=[1, 2, 2])
        self._act_live_point()
        self.assertEqual(self.svc._fo_memory_key[0], "app:4242")
        self.assertEqual(self.svc._settings["frame_os_games"]["app:4242"]["sessions"], 1)

        def session(launch, pairs):
            self.inspector.info["launch_key"] = launch
            for real in (45, 30, 30):
                self.feed(16, real, 90)
                self.step()
            self.svc.frame_os.proof.pairs["frames"].extend(pairs)
            self.feed(16, 30, 90)
            self.step()

        # two sessions measure boosts that bring nothing: the GPU cannot feed them here
        self.svc.frame_os.proof.pairs["frames"].extend([1.0, 0.5, 1.5, 0.0, 0.8])
        self.feed(16, 30, 90)
        self.step()
        record = self.svc._settings["frame_os_games"]["app:4242"]
        self.assertEqual(record["pairs"]["frames"], [1.0, 0.5, 1.5, 0.0, 0.8])
        self.assertEqual(record["off"], {}, "never switched off mid-session")
        self.feed(16, 30, 90)
        self.step()
        self.assertEqual(len(self.svc._settings["frame_os_games"]["app:4242"]["pairs"]["frames"]), 5,
                         "stored once, not again on the next steps")
        session([1, 3, 3], [0.2, 1.1, 0.9, 0.4])
        self.assertFalse(self.svc.frame_os.game_disabled["boost"])
        # a game exit (probe: not running) is no new memory session
        self.inspector.info.update(running=False)
        self.feed(16, 30, 90)
        self.step()
        self.assertEqual(self.svc._settings["frame_os_games"]["app:4242"]["sessions"], 2)
        self.inspector.info.update(running=True)
        # third launch: two sessions of evidence decide at its start
        session([1, 4, 4], [])
        self.assertEqual(self.svc._settings["frame_os_games"]["app:4242"]["sessions"], 3)
        self.assertEqual(self.svc._settings["frame_os_games"]["app:4242"]["off"], {"boost": 3})
        self.assertTrue(self.svc.frame_os.game_disabled["boost"])
        self.assertFalse(self.svc.frame_os.policy.boost_allowed)
        self.assertEqual(self.svc.get_status("game")["frame_os"]["game"]["verdicts"]["frames"], "useless")
        self.assertEqual(self.svc.frame_os.proof.summary()["frames"]["n"], 9, "earlier pairs counted once")
        # "Reset what GFG learned" forgets it too
        self.assertTrue(self.svc.forget_game_model("game")["success"])
        self.assertNotIn("app:4242", self.svc._settings["frame_os_games"])
        self.assertFalse(self.svc.frame_os.game_disabled["boost"])

    def test_act_injects_adaptive_overlay_only_while_the_pacer_is_live(self):
        self._act_live_point()
        self.assertIsNone(self.svc._injection, "no pacer telemetry yet: the renderer keeps the fixed ratio")
        self.svc.frame_os.last = {"telemetry": {"live": True}}
        self.feed(16, 30, 90)
        st = self.step()
        prof = self.overlay_profile()
        self.assertEqual((prof["adaptive"], prof["base_fps_cap"], prof["target_fps"]), (True, 45, 90))
        self.assertEqual(prof["adaptive_max_multiplier"], 3, "default capacity x3: rest stays at 30 real")
        self.assertFalse(prof["adaptive_stable_cadence"])
        self.assertEqual((st["state"], st["reason"]), ("LOCKED", "frame-os-act-holds-point"))
        writes = list(self.svc.power.writes)
        self.windows(3, 22, 90)              # rest cadence: never judged as a failing point
        self.assertEqual(self.svc._point["key"], "30x3")
        self.assertEqual(self.svc.power.writes[-1], writes[-1])
        # Act off: the next step takes the adaptive overlay back to the plain point
        self.svc.set_frame_os("game", "observe")
        self.feed(16, 30, 90)
        self.step()
        prof = self.overlay_profile()
        self.assertEqual((prof["adaptive"], prof["base_fps_cap"], prof["multiplier"]), (False, 30, 3))
        self.assertIsNone(self.svc._injection)

    def test_emergency_watts_are_written_without_frame_os(self):
        self.feed(20, 45, 90)
        self.step()
        self.feed(16, 30, 90)
        self.step()
        budget = self.svc._budget
        budget.tdp = budget.normal_max_w + 3.0          # guard-emergency-power above the normal cap
        self.svc._applied_tdp = None
        asyncio.run(self.svc._apply_budget_tdp("game"))
        self.assertEqual(self.svc.power.writes[-1], budget.normal_max_w + 3.0)

    def test_stale_telemetry_takes_the_act_overlay_back(self):
        self._act_live_point()
        self.svc.frame_os.last = {"telemetry": {"live": True}}
        self.feed(16, 30, 90)
        self.step()
        self.assertIsNotNone(self.svc._injection)
        asyncio.run(self.svc._drop_injection("game", "telemetry-stale"))
        self.assertIsNone(self.svc._injection)
        self.assertFalse(self.svc.frame_os.executor_active)
        self.assertFalse(self.overlay_profile()["adaptive"])

    def test_act_yields_to_the_governor_when_output_starves(self):
        self._act_live_point()
        self.svc.frame_os.last = {"telemetry": {"live": True}}
        self.feed(16, 30, 90)
        self.step()
        self.assertIsNotNone(self.svc._injection)
        self.assertTrue(self.svc.frame_os.executor_active)
        self.feed(20, 20, 60)                     # output far below target
        self.step()
        self.assertIsNone(self.svc._injection)
        self.assertFalse(self.svc.frame_os.executor_active)
        self.assertFalse(self.overlay_profile()["adaptive"])
        self.feed(16, 30, 90)                     # recovered, but the yield holds injection off
        self.step()
        self.assertIsNone(self.svc._injection, "no flapping right after a yield")

    def test_renderer_replan_is_not_a_false_motionboost_starvation(self):
        # The 8 October log captured two Act lockouts on a 1-2 sample
        # reconfiguration where output briefly equaled real. Never lock out
        # a feature before 4 s of settled evidence.
        self._act_live_point()
        self.svc.frame_os.last = {"telemetry": {"live": True}}
        self.feed(16, 30, 90)
        self.step()
        self.assertIsNotNone(self.svc._injection)
        for _ in range(2):
            self.feed(2, 30, 30, dt=0.5)
            self.step(0.1)
            self.assertIsNotNone(self.svc._injection, "transient re-plan is not starvation")
            self.feed(16, 30, 90)
            self.step()
        self.assertEqual(self.svc._injection_starvation_yields, 0)
        # A real, sustained outage must *still* release the overlay.
        self.feed(20, 20, 60)
        self.step()
        self.assertIsNone(self.svc._injection)
        self.assertEqual(self.svc._injection_starvation_yields, 1)

    def test_repeated_act_output_starvation_locks_out_injection_for_session(self):
        """A bad adaptive renderer must not cycle 16 times through 30-FPS drops."""
        self._act_live_point()
        self.svc.frame_os.last = {"telemetry": {"live": True}}
        self.feed(16, 30, 90)
        self.step()
        self.assertIsNotNone(self.svc._injection)
        self.feed(20, 20, 60)
        self.step()
        self.assertEqual(self.svc._injection_starvation_yields, 1)

        # Simulate the 60-second hold expiring. The second observed starvation
        # disables further Act injection, without disabling the Governor.
        self.svc._injection_hold_until = self.t["now"] - 1.0
        self.feed(16, 30, 90)
        self.step()
        self.assertIsNotNone(self.svc._injection)
        self.feed(20, 20, 60)
        self.step()
        self.assertEqual(self.svc._injection_starvation_yields, 2)
        self.assertTrue(self.svc.get_status("game")["frame_os"]["output_starvation_lockout"])
        self.assertFalse(self.svc.frame_os.executor_active)
        self.svc._injection_hold_until = self.t["now"] - 1.0
        self.feed(16, 30, 90)
        self.step()
        self.assertIsNone(self.svc._injection)
        self.assertTrue(self.svc.get_status("game")["enabled"])

    def test_act_starvation_lockout_does_not_leak_into_new_game(self):
        self._act_live_point()
        self.svc._injection_starvation_yields = 2
        self.svc._injection_hold_until = self.t["now"] + 999.0
        self.inspector.info["launch_key"] = [9, 9, 9]
        self.svc._launch_polled = -1e9
        st = self.step()
        self.assertEqual(st["reason"], "new-game-session")
        self.assertEqual(self.svc._injection_starvation_yields, 0)
        self.assertEqual(self.svc._injection_hold_until, 0.0)

    def test_stale_menu_event_does_not_disable_motionboost_starvation_guard(self):
        self._act_live_point()
        self.svc.frame_os.last = {"telemetry": {"live": True}}
        self.feed(16, 30, 90)
        self.step()
        self.assertIsNotNone(self.svc._injection)
        # A missed focus-restored event must not suppress the 60/90 output guard.
        self.svc.observer.game_focused = False
        self.svc.observer.game_focused_at = self.t["now"] - 9.0
        self.feed(20, 20, 60)
        self.step()
        self.assertIsNone(self.svc._injection, "starved Act must roll back despite stale Steam focus")
        self.assertFalse(self.svc.frame_os.executor_active)

    def test_a_long_steam_menu_never_locks_act_out(self):
        # review 1.3.0: focus is reported once; a menu open past 5 s was judged as a starved point
        self._act_live_point()
        self.svc.frame_os.last = {"telemetry": {"live": True}}
        self.feed(16, 30, 90)
        self.step()
        self.assertIsNotNone(self.svc._injection)
        for visit in range(3):
            self.svc.observer.game_focused = False
            self.svc.observer.game_focused_at = self.t["now"] - 20.0     # opened 20 s ago
            self.feed(20, 30, 30)                                         # generation suspended
            st = self.step()
            self.assertEqual((st["state"], st["reason"]), ("PAUSED", "steam-menu-open"))
            self.svc.observer.game_focused = True
            self.svc.observer.game_focused_at = self.t["now"]
            self.feed(16, 30, 90)
            self.step()
        self.assertEqual(self.svc._injection_starvation_yields, 0)
        self.assertIsNotNone(self.svc._injection, "Act still injects after three long menus")

    def test_long_steam_menu_does_not_poison_battery_or_act_memory(self):
        self._act_live_point()
        self.svc.frame_os.last = {"telemetry": {"live": True}}
        self.feed(16, 30, 90)
        self.step()
        self.assertIsNotNone(self.svc._injection)
        self.svc.observer.game_focused = False
        self.svc.observer.game_focused_at = self.t["now"] - (self.svc.MENU_MAX_S + 60)
        for _ in range(4):
            self.feed(20, 30, 30)
            st = self.step(2.0)
            self.assertEqual((st["state"], st["reason"]), ("PAUSED", "steam-menu-open"))
        self.assertEqual(self.svc._injection_starvation_yields, 0)

    def test_missed_focus_return_does_not_pause_forever(self):
        self.feed(20, 45, 90)
        self.step()
        self.feed(16, 30, 90)
        self.step()
        self.svc.observer.game_focused = False
        self.svc.observer.game_focused_at = self.t["now"] - (self.svc.MENU_MAX_S + 60)
        self.feed(20, 30, 90)
        self.assertNotEqual(self.step()["reason"], "steam-menu-open")

    def test_steam_menu_pauses_measuring_and_drops_its_samples(self):
        self.feed(20, 45, 90)
        self.step()
        self.feed(16, 30, 90)
        self.step()
        writes = list(self.svc.power.writes)
        self.svc.observer.game_focused = False
        self.feed(20, 30, 30)                     # generation suspended under the menu
        self.svc.observer.game_focused_at = self.t["now"]  # event and FPS share monotonic clock
        st = self.step()
        self.assertEqual((st["state"], st["reason"]), ("PAUSED", "steam-menu-open"))
        self.assertEqual(self.svc.power.writes, writes, "nothing changes while the menu is open")
        self.svc.observer.game_focused = True
        self.step()
        self.assertGreaterEqual(self.svc._evaluation_after_seq, self.svc.observer.sample_seq,
                                "menu samples are never judged")
        self.assertEqual(self.svc._point["key"], "30x3")

    def test_act_offset_is_applied_on_top_of_the_budget_cap(self):
        with patch.dict(os.environ, {"GFG_FRAME_OS_EXPERIMENTAL_ACT": "1"}):
            self.assertTrue(self.svc.set_frame_os("game", "act")["success"])
            self.assertTrue(self.svc.get_status("game")["frame_os"]["act_unlocked"])
            self.feed(20, 45, 90)
            self.step()
            self.feed(16, 30, 90)
            self.step()
            runner = self.svc.frame_os
            runner.last = {"decision": {"tdp_w": runner.policy.broker.calm_w + 4.0}}
            runner.executor_active = True
            self.svc._applied_tdp = None
            asyncio.run(self.svc._apply_budget_tdp("game"))
            self.assertEqual(self.svc.power.writes[-1], min(self.svc._budget.normal_max_w, self.svc._budget.tdp + 4.0))


class RingRefreshTests(unittest.TestCase):
    """Use real publication logic and fake only the rasterizer/clock."""
    def setUp(self):
        from gfg_plugin import hud_rings
        self.rings = hud_rings
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.svc = GovernorService.__new__(GovernorService)
        self.svc.ring_hud_path = Path(self.temp.name) / "hud.raw"
        self.svc.ring_hud_extent = Path(self.temp.name) / "hud.extent"
        self.svc.ring_hud_extent.write_text("1280 800 1")
        self.svc._ring_hud_lock = __import__("threading").Lock()
        self.svc._ring_hud_key = None
        self.svc._ring_hud_due = 0.0
        self.svc._ring_hud_seq = 0
        self.svc._launch = {"launch_key": [1, 2, 3]}
        self.now = 100.0
        self.svc._clock = lambda: self.now
        self.settings = {"preset": "minimal", "position": "top-left"}
        self.status = {"enabled": True, "target_output_fps": 90,
                       "telemetry": {"snapshot": {"sample_age_ms": 100,
                                     "latest": {"real_fps": 45, "output_fps": 90}},
                                     "summary": {"output": {"median": 60}, "real": {"median": 30}}}}
        self.writes = []
        self.fail = False

        def writer(data, **kwargs):
            self.writes.append((data, kwargs))
            if self.fail:
                return False
            self.svc.ring_hud_path.write_bytes(b"published")
            return True

        self.patch = patch.object(hud_rings, "write_overlay", side_effect=writer)
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def publish(self):
        return self.svc._publish_ring_hud(self.status, self.settings)

    def test_one_second_refresh_and_latest_fps(self):
        self.assertTrue(self.publish())
        self.assertEqual(self.writes[-1][0]["fps"], 90)
        self.status["telemetry"]["snapshot"]["latest"]["output_fps"] = 70
        self.now += 0.5
        self.publish()
        self.assertEqual(len(self.writes), 1)
        self.now += 0.5
        self.publish()
        self.assertEqual(self.writes[-1][0]["fps"], 70)

    def test_identical_visible_data_skips_render_and_write(self):
        self.publish()
        self.now += 1
        self.publish()
        self.assertEqual(len(self.writes), 1)
        self.svc.ring_hud_path.unlink()
        self.now += 1
        self.publish()
        self.assertEqual(len(self.writes), 2, "missing file is recreated")

    def test_resize_republishes_at_new_scale(self):
        self.publish()
        self.svc.ring_hud_extent.write_text("3840 2160 1")
        self.now += 1
        self.publish()
        self.assertEqual(self.writes[-1][1]["scale"], 3.0)
        self.assertEqual(len(self.writes), 2)

    def test_stale_and_nonfinite_fps_are_not_displayed(self):
        # field report 1.3: one late sample flipped the number to "—" and back (flicker); the last
        # good value is held for HUD_HOLD_S, never longer
        self.publish()
        self.status["telemetry"]["snapshot"]["sample_age_ms"] = 3000
        self.now += 1
        self.publish()
        self.assertEqual(self.writes[-1][0]["fps"], 90, "a late sample keeps the picture steady")
        self.status["telemetry"]["snapshot"]["latest"]["output_fps"] = float("nan")
        self.status["telemetry"]["snapshot"]["sample_age_ms"] = 10
        self.now += self.svc.HUD_HOLD_S + 1
        self.publish()
        self.assertIsNone(self.writes[-1][0]["fps"], "stale beyond the hold, or not a number: unavailable")
        self.status["telemetry"]["snapshot"]["latest"]["output_fps"] = 88
        self.now += 1
        self.publish()
        self.assertEqual(self.writes[-1][0]["fps"], 88)

    def test_failed_publish_is_retried_without_committing_sequence(self):
        self.fail = True
        self.assertFalse(self.publish())
        self.assertEqual(self.svc._ring_hud_seq, 0)
        self.fail = False
        self.assertTrue(self.publish())
        self.assertEqual(self.svc._ring_hud_seq, 1)

    def test_failed_clear_retries_and_reenable_republishes(self):
        self.publish()
        self.fail = True
        self.svc._clear_ring_hud()
        self.assertNotEqual(self.svc._ring_hud_due, -1)
        self.fail = False
        self.svc._clear_ring_hud()
        self.assertEqual(self.svc._ring_hud_due, -1)
        self.assertTrue(self.publish())
        self.assertIsNotNone(self.writes[-1][0])

    def test_session_change_republishes_even_with_same_numbers(self):
        self.publish()
        self.svc._launch = {"launch_key": [4, 5, 6]}
        self.now += 1
        self.publish()
        self.assertEqual(len(self.writes), 2)

    def test_motionboost_badge_requires_executor_pacer_ack_and_measured_frames(self):
        self.settings["preset"] = "standard"
        self.svc.frame_os = types.SimpleNamespace(
            executor_active=True, policy=types.SimpleNamespace(calm_real_hz=30.0))
        self.status["frame_os"] = {
            "enabled": True, "mode": "act", "acknowledged": True,
            "decision": {"level": "boost"}, "telemetry": {"live": True},
            "benefit": {"ready": True, "frames_pct": 50.0, "response_pct": None, "energy_pct": 0.0},
        }
        self.publish()
        data = self.writes[-1][0]["frame_os"]
        self.assertTrue(data["verified_boost"])
        self.assertEqual((data["actual_real"], data["actual_ratio"]), (45, 2.0))
        self.status["frame_os"]["acknowledged"] = False
        self.now += 1.0
        self.publish()
        self.assertFalse(self.writes[-1][0]["frame_os"]["verified_boost"])
        self.status["frame_os"]["acknowledged"] = True
        self.status["telemetry"]["snapshot"]["latest"]["real_fps"] = 30
        self.now += 1.0
        self.publish()
        self.assertFalse(self.writes[-1][0]["frame_os"]["verified_boost"])
        self.svc.frame_os.executor_active = False
        self.now += 1.0
        self.publish()
        self.assertFalse(self.writes[-1][0]["frame_os"]["active"])
        self.svc.frame_os.executor_active = True
        self.status["telemetry"]["snapshot"]["sample_age_ms"] = 3000
        self.now += 1.0
        self.publish()
        self.assertFalse(self.writes[-1][0]["frame_os"]["verified_boost"])

    def test_a_probe_glitch_does_not_swap_rings_for_text(self):
        live = [True]
        self.svc._ring_hud_live = lambda: live[0]
        self.assertTrue(self.svc._ring_hud_live_steady())
        live[0] = False                   # the launch probe said "not running" once
        self.now += 1
        self.assertTrue(self.svc._ring_hud_live_steady())
        self.now += self.svc.HUD_HOLD_S + 1
        self.assertFalse(self.svc._ring_hud_live_steady(), "a real exit still falls back")

    def test_frame_os_rings_survive_a_missed_telemetry_beat(self):
        self.settings["preset"] = "standard"
        self.svc.frame_os = types.SimpleNamespace(executor_active=False, policy=None)
        self.status["frame_os"] = {"enabled": True, "mode": "observe", "decision": {"level": "calm"},
                                   "telemetry": {"live": True},
                                   "benefit": {"ready": True, "response_pct": 40.0, "frames_pct": 10.0}}
        self.publish()
        self.assertIn("frame_os", self.writes[-1][0])
        self.status["frame_os"]["telemetry"]["live"] = False
        self.now += 1
        self.publish()
        self.assertIn("frame_os", self.writes[-1][0], "no resize for one missed beat")
        self.now += self.svc.HUD_HOLD_S + 1
        self.publish()
        self.assertNotIn("frame_os", self.writes[-1][0], "a dead Frame OS goes after the hold")

    def test_dead_frame_os_does_not_show_old_benefit_rings(self):
        self.status["frame_os"] = {"enabled": True, "telemetry": {"live": False},
                                   "benefit": {"ready": True, "response_pct": 50}}
        self.publish()
        self.assertNotIn("frame_os", self.writes[-1][0])
