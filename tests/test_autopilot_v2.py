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
                ceiling_w=15, fresh=True, samples=8, gpu_clock_available=True, preference="auto")
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
        self.assertEqual(policy.update(90, 45, 90, "auto", True), 90)
        self.assertEqual(policy.update(90, 20, 40, "auto", True), 90)
        self.assertEqual(policy.update(90, 20, 40, "auto", True), 90)
        self.assertEqual(policy.update(90, 20, 40, "auto", True), 60)


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
            held = self._summary(45, 90)
            bad = self._summary(20, 40)
            self.assertEqual(svc._governor_target("game", 90, held), 90)
            self.assertEqual(svc._governor_target("game", 90, bad), 90)
            self.assertEqual(svc._governor_target("game", 90, bad), 90)
            self.assertEqual(svc._governor_target("game", 90, bad), 60)
            self.assertEqual(svc._status.get("target_output_fps"), None)
            target = svc._governor_target("game", 90, bad)
            svc._status["target_output_fps"] = target
            self.assertNotEqual(svc._budget.target_output_fps, target)
            svc._evaluation_after_seq = svc.observer.sample_seq
            svc._budget = BudgetController(target_output_fps=target, now=1.0)
            self.assertEqual(svc._budget.target_output_fps, 60)
            self.assertEqual(svc._status["target_output_fps"], 60)
            good = self._summary(45, 90)
            self.assertEqual(svc._governor_target("game", 90, good), 60)
            self.assertEqual(svc._governor_target("game", 90, good), 60)
            self.assertEqual(svc._governor_target("game", 90, good), 90)
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

