"""Autopilot 2.0: planner, arbiter, GPU clock ceiling, HUD rings, Extreme migration."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "py_modules"))
from gfg_plugin.autopilot.arbiter import Arbiter
from gfg_plugin.autopilot.gpu_clock import GpuClock, MemoryBackend
from gfg_plugin.autopilot.hud_tone import tones
from gfg_plugin.autopilot.planner import TargetPolicy, View, decide
from gfg_plugin import hud_rings


def measured(**kwargs):
    row = {"samples": 6, "span_s": 3.0, "session": None}
    row.update(kwargs)
    return row


def view(**kwargs):
    base = dict(real_fps=45, output_fps=90, frametime_p95_ms=22, target_fps=90,
                gpu_busy=40, cpu_busy=30, gpu_mhz=1200, temp_c=55, draw_w=10,
                ceiling_w=15, fresh=True, samples=8, gpu_clock_available=True, preference="auto",
                battery_pct=80, battery_minutes=120, tdp_readable=True)
    base.update(kwargs)
    return View(**base)


class PlannerTests(unittest.TestCase):
    def test_a_target_is_not_a_measured_frame_rate(self):
        decision = decide(view(real_fps=None, output_fps=None, fresh=False, samples=0, target_fps=90))
        self.assertEqual(decision.action, "PAUSE")
        self.assertIsNone(decision.measured_real_fps)

    def test_stable_play_holds_when_there_is_no_headroom(self):
        self.assertEqual(decide(view(draw_w=14, ceiling_w=15)).action, "HOLD")

    def test_cpu_limit_asks_for_one_gpu_clock_step(self):
        decision = decide(view(real_fps=28, output_fps=56, cpu_busy=95, gpu_busy=40))
        self.assertEqual(decision.action, "OPTIMIZE_GPU_CLOCK")

    def test_missing_gpu_clock_does_not_invent_a_clock_change(self):
        decision = decide(view(real_fps=28, output_fps=56, cpu_busy=95, gpu_busy=40, gpu_clock_available=False))
        self.assertNotEqual(decision.action, "OPTIMIZE_GPU_CLOCK")

    def test_unknown_limit_holds(self):
        decision = decide(view(real_fps=28, output_fps=56, cpu_busy=50, gpu_busy=50, draw_w=8, ceiling_w=15))
        self.assertEqual(decision.reason, "bottleneck-unknown")

    def test_heat_stops_experiments(self):
        self.assertEqual(decide(view(temp_c=92)).action, "PAUSE")
        self.assertEqual(decide(view(temp_c=86)).action, "HOLD")


class ArbiterTests(unittest.TestCase):
    def test_a_drop_blocks_until_rollback_is_confirmed(self):
        arbiter = Arbiter()
        arbiter.begin("gpu-clock", "probable-cpu-bottleneck", 0, {"real": 40, "output": 80, "sample_seq": 1})
        self.assertEqual(arbiter.admit("OPTIMIZE_POWER", 1), "busy")
        self.assertEqual(arbiter.judge(1, measured(real=30, output=60, sample_seq=2)), "rollback")
        self.assertTrue(arbiter.freeze_tdp)
        arbiter.finish_rollback()
        self.assertFalse(arbiter.freeze_tdp)

    def test_no_measurable_gain_rolls_back(self):
        arbiter = Arbiter()
        arbiter.begin("gpu-clock", "check", 0, {"real": 40, "output": 80, "sample_seq": 1, "frametime_p95": 22})
        arbiter.judge(3, measured(real=39, output=79, sample_seq=2, frametime_p95=22))
        self.assertEqual(arbiter.judge(12, measured(real=39, output=79, sample_seq=4, frametime_p95=22)), "rollback")
        self.assertEqual(arbiter.reason, "no-measurable-gain")

    def test_a_real_gain_needs_a_sample_from_after_the_change(self):
        arbiter = Arbiter()
        arbiter.begin("gpu-clock", "check", 0, {"real": 30, "output": 60, "sample_seq": 5, "frametime_p95": 30})
        self.assertEqual(arbiter.judge(20, measured(real=40, output=80, sample_seq=5, frametime_p95=25)), "wait")
        arbiter.judge(3, measured(real=36, output=72, sample_seq=6, frametime_p95=28))
        self.assertEqual(arbiter.judge(12, measured(real=36, output=72, sample_seq=7, frametime_p95=28)), "accept")


class GpuClockTests(unittest.TestCase):
    def test_real_writes_are_off_by_default(self):
        clock = GpuClock(backend=MemoryBackend(), writes_enabled=False)
        self.assertEqual(clock.lower_ceiling()["reason"], "writes-disabled")
        self.assertEqual(clock.backend.level, "auto")

    def test_a_failed_commit_restores_or_stays_locked(self):
        clock = GpuClock(backend=MemoryBackend(fail_at="commit"), writes_enabled=True)
        result = clock.lower_ceiling()
        self.assertFalse(result["applied"])
        self.assertTrue(clock.owned)
        self.assertEqual(clock.phase, "restore-pending")

    def test_a_failed_restore_keeps_the_lock(self):
        backend = MemoryBackend()
        clock = GpuClock(backend=backend, writes_enabled=True)
        self.assertTrue(clock.lower_ceiling()["applied"])
        backend.fail_at = "level"
        self.assertFalse(clock.restore()["restored"])
        self.assertEqual(clock.phase, "restore-pending")
        self.assertEqual(clock.lower_ceiling()["reason"], "restore-pending")

    def test_a_user_clock_is_not_overwritten(self):
        clock = GpuClock(backend=MemoryBackend(), writes_enabled=True)
        clock.lower_ceiling()
        clock.backend.maximum = 900
        result = clock.restore()
        self.assertTrue(result.get("yielded"))
        self.assertEqual(clock.backend.maximum, 900)

    def test_a_receipt_is_reloaded(self):
        path = Path(tempfile.mkdtemp()) / "receipt.json"
        backend = MemoryBackend()
        GpuClock(backend=backend, writes_enabled=True, receipt_path=path).lower_ceiling()
        restored = GpuClock(backend=backend, writes_enabled=False, receipt_path=path)
        self.assertTrue(restored.restore()["restored"])
        self.assertEqual(backend.level, "auto")


class HoldAndTargetTests(unittest.TestCase):
    def test_hold_keeps_a_healthy_budget_from_probing(self):
        from gfg_plugin.governor_core import BudgetController, WindowVerdict
        ctl = BudgetController(target_output_fps=90, now=0.0)
        ctl.phase = "locked"
        ctl.locked_since = 0.0
        ctl.hold_planned = True
        self.assertEqual(ctl.observe(1000.0, WindowVerdict(True, False, "ok"), 45, 90), "hold")

    def test_the_display_target_does_not_flap(self):
        policy = TargetPolicy()
        def observe(real, output, first, last, now):
            return policy.update(90, real, output, "auto", True,
                                 sample_seq=last, first_sample_seq=first, span_s=4, now=now)
        self.assertEqual(observe(45, 90, 1, 10, 0), 90)
        self.assertEqual(observe(20, 40, 11, 20, 10), 90)
        # Duplicate or overlapping sliding windows are not independent misses.
        self.assertEqual(observe(20, 40, 11, 20, 11), 90)
        self.assertEqual(observe(20, 40, 12, 21, 12), 90)
        self.assertEqual(observe(20, 40, 22, 30, 20), 90)
        self.assertEqual(observe(20, 40, 31, 40, 30), 60)
        # A game delivering a steady 60 under its new cap cannot prove 90 FPS
        # without a guarded retry. Wait 90 s, then require fresh healthy windows.
        self.assertEqual(observe(30, 60, 41, 50, 110), 60)
        self.assertEqual(observe(30, 60, 51, 60, 120), 60)
        self.assertEqual(observe(30, 60, 61, 70, 130), 60)
        self.assertEqual(observe(30, 60, 71, 80, 140), 90)
        # A failed retry backs off; it must not immediately bounce to 90 again.
        observe(20, 40, 81, 90, 150)
        observe(20, 40, 91, 100, 160)
        self.assertEqual(observe(20, 40, 101, 110, 170), 60)
        self.assertEqual(observe(30, 60, 111, 120, 210), 60)


class HudTests(unittest.TestCase):
    def test_autopilot_uses_one_palette_and_does_not_duplicate_fps(self):
        calm = tones(view(frametime_p95_ms=22.2, multiplier=2, multiplier_confirmed=True))
        self.assertEqual(calm["fps"], "green")
        self.assertEqual(calm["battery"], "green")
        self.assertEqual(tones(view(fresh=False, real_fps=None, output_fps=None))["fps"], "grey")
        data = {"fps": 90, "real": 45, "target": 90, "tdp": 12, "limit": 15,
                "battery_pct": 80, "autopilot": {"active": True, "tones": calm, "gpu_mhz": 1100,
                                                 "cpu_pct": 40, "temp_c": 50, "frametime_ms": 22}}
        items = hud_rings.items_for(data, "detailed")
        labels = [item.get("label") for item in items]
        self.assertEqual(labels.count("FPS"), 1)
        self.assertEqual(labels.count("TDP"), 1)
        self.assertEqual(labels.count("BATTERY"), 1)
        for name in ("GPU", "CPU", "TEMP", "FRAME", "ENERGY"):
            self.assertIn(name, labels)
        green = (46, 170, 96)
        rings = [item for item in items if item.get("kind") == "ring"]
        self.assertTrue(all(item["rgb"] == green for item in rings))


class ColorAndModeRegressionTests(unittest.TestCase):
    def test_smoothness_compares_real_frametime_with_real_cadence(self):
        from gfg_plugin.autopilot.planner import decide
        stable = view(real_fps=45, output_fps=90, target_fps=90,
                      frametime_p95_ms=22.2, multiplier=2, multiplier_confirmed=True,
                      preference="smoothness")
        self.assertEqual(decide(stable).action, "HOLD")

    def test_battery_and_power_tones_are_not_always_green(self):
        self.assertEqual(tones(view(battery_pct=5))["battery"], "red")
        self.assertEqual(tones(view(battery_pct=17))["battery"], "yellow")
        self.assertEqual(tones(view(battery_pct=None))["battery"], "grey")
        self.assertEqual(tones(view(tdp_external_change=True))["tdp"], "yellow")
        self.assertEqual(tones(view(tdp_error="restore failed"))["tdp"], "red")
        self.assertEqual(tones(view(tdp_readable=False))["tdp"], "grey")

    def test_mode_switch_releases_the_autopilot_plan_lock(self):
        import test_governor_runtime as legacy
        fixture = legacy.RuntimeBase()
        fixture.setUp()
        try:
            svc = fixture.svc
            svc._settings.setdefault("profiles", {}).setdefault("game", {})["enabled"] = True
            svc.set_mode("game", "autopilot")
            svc._active_profile = "game"
            svc._autopilot_plan = "hold"
            svc._status["autopilot"] = {"enabled": True, "active": True}
            self.assertTrue(svc._autopilot_blocks_planned())
            svc.set_mode("game", "quality")
            self.assertFalse(svc._autopilot_blocks_planned())
            self.assertEqual(svc._autopilot_plan, "off")
            self.assertFalse(svc._status["autopilot"]["active"])
        finally:
            fixture.tearDown()


class MigrationTests(unittest.TestCase):
    def test_saved_extreme_opens_as_autopilot(self):
        import test_governor_runtime as legacy
        fixture = legacy.RuntimeBase()
        fixture.setUp()
        try:
            svc = fixture.svc
            svc._settings = {"schema": 1, "profiles": {"game": {"mode": "extreme", "enabled": True}}}
            self.assertTrue(svc._migrate_extreme_mode())
            self.assertEqual(svc._mode("game"), "autopilot")
        finally:
            fixture.tearDown()


class LifecycleTests(unittest.TestCase):
    def test_leaving_autopilot_and_a_dead_game_restore_the_mock(self):
        import test_governor_runtime as legacy
        fixture = legacy.RuntimeBase()
        fixture.setUp()
        try:
            svc = fixture.svc
            backend = MemoryBackend()
            svc._autopilot_gpu = GpuClock(backend=backend, writes_enabled=True)
            svc._autopilot_gpu.lower_ceiling()
            svc.set_mode("game", "quality")
            self.assertEqual(backend.level, "auto")
            svc._autopilot_gpu = GpuClock(backend=backend, writes_enabled=True)
            svc.set_mode("game", "autopilot")
            svc._autopilot_gpu.lower_ceiling()
            svc._active_profile = "game"
            svc._launch = {"running": False, "reason": "exited"}
            svc._autopilot_maintain()
            self.assertFalse(svc._autopilot_gpu.owned)
        finally:
            fixture.tearDown()

    def test_unconfirmed_rollback_stays_blocked(self):
        import test_governor_runtime as legacy
        fixture = legacy.RuntimeBase()
        fixture.setUp()
        try:
            svc = fixture.svc
            backend = MemoryBackend()
            svc._autopilot_gpu = GpuClock(backend=backend, writes_enabled=True)
            svc._autopilot_gpu.lower_ceiling()
            svc._autopilot_arbiter.begin("gpu-clock", "check", 0, {"real": 40, "output": 80, "sample_seq": 1})
            svc._autopilot_arbiter.judge(1, measured(real=20, output=40, sample_seq=2))
            backend.fail_at = "level"
            self.assertFalse(svc._restore_autopilot_gpu("rollback"))
            self.assertEqual(svc._autopilot_arbiter.state, "RESTORE_PENDING")
            self.assertEqual(svc._autopilot_arbiter.admit("OPTIMIZE_GPU_CLOCK", 50), "busy")
        finally:
            fixture.tearDown()


class FrameToneTests(unittest.TestCase):
    def test_real_frametime_follows_the_confirmed_multiplier(self):
        stable_x2 = tones(view(real_fps=45, output_fps=90, target_fps=90, frametime_p95_ms=22.2,
                                multiplier=2, multiplier_confirmed=True))
        stable_x3 = tones(view(real_fps=30, output_fps=90, target_fps=90, frametime_p95_ms=33.3,
                                multiplier=3, multiplier_confirmed=True))
        uneven = tones(view(real_fps=45, output_fps=90, target_fps=90, frametime_p95_ms=22.2,
                            frametime_jitter_ms=12, multiplier=2, multiplier_confirmed=True))
        dropped = tones(view(real_fps=45, output_fps=90, target_fps=90, frametime_p95_ms=50,
                             multiplier=2, multiplier_confirmed=True))
        unknown = tones(view(frametime_p95_ms=22.2, multiplier=2, multiplier_confirmed=False))
        self.assertEqual(stable_x2["frame"], "green")
        self.assertEqual(stable_x3["frame"], "green")
        self.assertEqual(uneven["frame"], "yellow")
        self.assertEqual(dropped["frame"], "red")
        self.assertEqual(unknown["frame"], "grey")


class GoalAndPauseTests(unittest.TestCase):
    def _summary(self, real, output):
        return {"samples": 8, "sample_span_s": 4, "last_sample_seq": 9,
                "real": {"median": real}, "output": {"median": output},
                "multiplier": {"median": 2}, "frametime": {"p95_ms": 22, "p99_ms": 24, "jitter_ms": 1}}

    def test_a_sustained_miss_becomes_the_governor_target(self):
        import test_governor_runtime as legacy
        from gfg_plugin.governor_core import BudgetController
        fixture = legacy.RuntimeBase()
        fixture.setUp()
        try:
            svc = fixture.svc
            svc._settings.setdefault("profiles", {}).setdefault("game", {})["enabled"] = True
            svc.set_mode("game", "autopilot")
            svc._budget = BudgetController(target_output_fps=90, now=0.0)
            now = {"value": 0}
            svc._clock = lambda: now["value"]

            def evidence(real, output, first, last, time):
                now["value"] = time
                row = self._summary(real, output)
                row["first_sample_seq"], row["last_sample_seq"] = first, last
                return svc._governor_target("game", 90, row)

            self.assertEqual(evidence(45, 90, 1, 10, 0), 90)
            self.assertEqual(evidence(20, 40, 11, 20, 10), 90)
            self.assertEqual(evidence(20, 40, 21, 30, 20), 90)
            self.assertEqual(evidence(20, 40, 31, 40, 30), 60)
            self.assertEqual(evidence(20, 40, 31, 40, 31), 60)
            # The chosen goal is forwarded by _iteration_core into _budget_step
            # and must replace any BudgetController made for the previous goal.
            target = evidence(20, 40, 31, 40, 32)
            self.assertNotEqual(svc._budget.target_output_fps, target)
            svc._budget = BudgetController(target_output_fps=target, now=32)
            self.assertEqual(svc._budget.target_output_fps, 60)
            self.assertEqual(evidence(30, 60, 41, 50, 130), 60)
            self.assertEqual(evidence(30, 60, 51, 60, 140), 60)
            self.assertEqual(evidence(30, 60, 61, 70, 150), 90)
        finally:
            fixture.tearDown()

    def test_pause_blocks_a_planned_power_probe(self):
        import asyncio
        import test_governor_runtime as legacy
        from gfg_plugin.governor_core import BudgetController, WindowVerdict
        fixture = legacy.RuntimeBase()
        fixture.setUp()
        try:
            svc = fixture.svc
            svc._settings.setdefault("profiles", {}).setdefault("game", {})["enabled"] = True
            svc.set_mode("game", "autopilot")
            svc._active_profile = "game"
            svc._status["sensors"] = {"temp_c": 92}
            svc._budget = BudgetController(target_output_fps=90, now=0.0)
            svc._budget.phase = "locked"
            svc._budget.locked_since = 0.0
            seen = {}

            def summary(window, after_seq=0, **kwargs):
                seen["after_seq"] = after_seq
                return {"samples": 0, "sample_span_s": 0, "last_sample_seq": after_seq}

            svc.observer.summary = summary
            asyncio.run(svc._autopilot_tick("game", self._summary(45, 90), 90))
            self.assertEqual(svc._autopilot_plan, "pause")
            self.assertTrue(svc._budget.hold_planned)
            self.assertTrue(svc._autopilot_blocks_planned())
            self.assertEqual(svc._budget.observe(1000.0, WindowVerdict(True, False, "ok"), 45, 90), "hold")
        finally:
            fixture.tearDown()

    def test_a_clock_check_asks_for_samples_after_the_change(self):
        import asyncio
        import test_governor_runtime as legacy
        fixture = legacy.RuntimeBase()
        fixture.setUp()
        try:
            svc = fixture.svc
            svc._settings.setdefault("profiles", {}).setdefault("game", {})["enabled"] = True
            svc.set_mode("game", "autopilot")
            svc._autopilot_arbiter.begin("gpu-clock", "check", 0, measured(real=30, output=60, sample_seq=4, session=("game", "None", None)))
            seen = {}

            def summary(window, after_seq=0, **kwargs):
                seen["after_seq"] = after_seq
                return {"samples": 6, "sample_span_s": 3, "last_sample_seq": after_seq + 1,
                        "real": {"median": 36}, "output": {"median": 72},
                        "frametime": {"p95_ms": 28}}

            svc.observer.summary = summary
            asyncio.run(svc._autopilot_tick("game", self._summary(30, 60), 90))
            self.assertEqual(seen["after_seq"], 4)
        finally:
            fixture.tearDown()

    def test_steam_menu_and_unconfirmed_point_block_all_gpu_trials(self):
        import test_governor_runtime as legacy
        fixture = legacy.RuntimeBase()
        fixture.setUp()
        try:
            svc = fixture.svc
            svc._active_profile = "game"
            svc.set_mode("game", "autopilot")
            svc._point = {"key": "30x3", "base_target_fps": 30, "multiplier": 3,
                          "target_output_fps": 90}
            svc._point_mode = "applied"
            svc._request = None
            svc._evaluation_after_seq = 10
            svc._menu_covering = lambda: False
            stable = {"samples": 9, "sample_span_s": 9.0,
                      "first_sample_seq": 11, "last_sample_seq": 20,
                      "real": {"median": 30}, "output": {"median": 90},
                      "multiplier": {"median": 3}}
            self.assertEqual(svc._autopilot_trial_ready(stable, 90),
                             (True, "confirmed-game-cadence"))
            svc._menu_covering = lambda: True
            self.assertEqual(svc._autopilot_trial_ready(stable, 90)[1],
                             "steam-menu-open")
            svc._menu_covering = lambda: False
            svc._menu_since = 10.0
            self.assertEqual(svc._autopilot_trial_ready(stable, 90)[1],
                             "steam-menu-open")
            svc._menu_since = None
            # The first physical test dipped from 90 to 42 Output when
            # Gamescope opened the Steam menu; it must never trial VRS.
            dipped = {**stable, "output": {"median": 42.674},
                      "multiplier": {"median": 1.45}}
            self.assertEqual(svc._autopilot_trial_ready(dipped, 90)[1],
                             "renderer-not-stable")
            svc._point = None
            # The second log trial started BEFORE point 30x3 was confirmed.
            self.assertEqual(svc._autopilot_trial_ready(stable, 90)[1],
                             "point-not-confirmed")
            svc._point = {"key": "30x3", "base_target_fps": 30, "multiplier": 3,
                          "target_output_fps": 90}
            resumed = {**stable, "first_sample_seq": 10}
            self.assertEqual(svc._autopilot_trial_ready(resumed, 90)[1],
                             "baseline-overlaps-transition")
        finally:
            fixture.tearDown()

    def test_stop_clears_the_autopilot_hud_session(self):
        import test_governor_runtime as legacy
        fixture = legacy.RuntimeBase()
        fixture.setUp()
        try:
            svc = fixture.svc
            svc._autopilot_plan = "hold"
            svc._status["autopilot"] = {"enabled": True, "active": True, "tones": {"fps": "green"}}
            svc._clear_autopilot_session("governor-disabled")
            self.assertFalse(svc._status["autopilot"]["active"])
            self.assertEqual(svc._autopilot_plan, "off")
        finally:
            fixture.tearDown()


if __name__ == "__main__":
    unittest.main()

