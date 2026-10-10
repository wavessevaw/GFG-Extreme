"""Autopilot 2.0: planner, arbiter, GPU clock ceiling, HUD rings, Extreme migration."""
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "py_modules"))
from gfg_plugin.autopilot.arbiter import Arbiter
from gfg_plugin.autopilot.gpu_clock import GpuClock
from gfg_plugin.autopilot.hud_tone import tones
from gfg_plugin.autopilot.planner import View, decide
from gfg_plugin import hud_rings


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
        self.assertNotEqual(decision.reason, "already-efficient")

    def test_stable_play_holds_when_there_is_no_headroom(self):
        decision = decide(view(draw_w=14, ceiling_w=15))
        self.assertEqual(decision.action, "HOLD")
        self.assertEqual(decision.tool, "none")

    def test_cpu_limit_asks_for_one_gpu_clock_step(self):
        decision = decide(view(real_fps=28, output_fps=56, cpu_busy=95, gpu_busy=40))
        self.assertEqual(decision.action, "OPTIMIZE_GPU_CLOCK")
        self.assertEqual(decision.tool, "gpu-clock")

    def test_missing_gpu_clock_does_not_invent_a_clock_change(self):
        decision = decide(view(real_fps=28, output_fps=56, cpu_busy=95, gpu_busy=40, gpu_clock_available=False))
        self.assertNotEqual(decision.action, "OPTIMIZE_GPU_CLOCK")

    def test_unknown_limit_holds(self):
        decision = decide(view(real_fps=28, output_fps=56, cpu_busy=50, gpu_busy=50, draw_w=8, ceiling_w=15))
        self.assertEqual(decision.action, "HOLD")
        self.assertEqual(decision.reason, "bottleneck-unknown")

    def test_heat_stops_experiments(self):
        self.assertEqual(decide(view(temp_c=92)).action, "PAUSE")
        self.assertEqual(decide(view(temp_c=86)).action, "HOLD")


class ArbiterTests(unittest.TestCase):
    def test_a_gpu_trial_freezes_tdp_until_it_is_judged(self):
        arbiter = Arbiter()
        self.assertEqual(arbiter.admit("OPTIMIZE_GPU_CLOCK", 10), "ok")
        arbiter.begin("gpu-clock", "probable-cpu-bottleneck", 10, (40, 80))
        self.assertTrue(arbiter.freeze_tdp)
        self.assertEqual(arbiter.admit("OPTIMIZE_POWER", 11), "busy")
        self.assertEqual(arbiter.judge(15, 30, 60), "rollback")
        arbiter.finish_rollback()
        self.assertFalse(arbiter.freeze_tdp)
        self.assertEqual(arbiter.admit("OPTIMIZE_GPU_CLOCK", 50), "rejected")

    def test_a_verified_gain_is_held(self):
        arbiter = Arbiter()
        arbiter.begin("gpu-clock", "probable-cpu-bottleneck", 0, (30, 60))
        self.assertEqual(arbiter.judge(5, 36, 72), "wait")
        self.assertEqual(arbiter.judge(11, 36, 72), "accept")
        self.assertEqual(arbiter.state, "HOLD")
        self.assertFalse(arbiter.freeze_tdp)


class GpuClockTests(unittest.TestCase):
    def test_missing_files_write_nothing(self):
        clock = GpuClock(root=tempfile.mkdtemp())
        self.assertFalse(clock.status()["available"])
        self.assertEqual(clock.lower_ceiling()["reason"], "GPU_CLOCK_UNAVAILABLE")
        self.assertFalse(clock.owned)

    def test_one_step_then_restore(self):
        root = tempfile.mkdtemp()
        device = Path(root) / "card0" / "device"
        device.mkdir(parents=True)
        level = device / "power_dpm_force_performance_level"
        table = device / "pp_od_clk_voltage"
        level.write_text("auto\n")
        table.write_text("OD_SCLK:\n0: 200Mhz\n1: 1600Mhz\nOD_RANGE:\nSCLK: 200Mhz 1600Mhz\n")
        clock = GpuClock(root=root)
        lowered = clock.lower_ceiling()
        self.assertTrue(lowered["applied"])
        self.assertEqual(lowered["limit_mhz"], 1500)
        self.assertEqual(level.read_text(), "manual")
        self.assertTrue(clock.owned)
        restored = clock.restore()
        self.assertTrue(restored["restored"])
        self.assertFalse(clock.owned)
        self.assertEqual(level.read_text(), "auto")


class HudTests(unittest.TestCase):
    def test_autopilot_adds_gpu_cpu_temp_and_frame_without_a_second_fps_ring(self):
        calm = tones(view())
        self.assertEqual(calm["fps"], "green")
        self.assertEqual(tones(view(fresh=False, real_fps=None, output_fps=None))["fps"], "grey")
        data = {"fps": 90, "real": 45, "target": 90, "tdp": 12, "limit": 15,
                "autopilot": {"active": True, "tones": calm, "gpu_mhz": 1100,
                              "cpu_pct": 40, "temp_c": 50, "frametime_ms": 22}}
        labels = [item.get("label") for item in hud_rings.items_for(data, "detailed")]
        self.assertEqual(labels.count("FPS"), 1)
        self.assertEqual(labels.count("TDP"), 1)
        self.assertIn("GPU", labels)
        self.assertIn("CPU", labels)
        self.assertIn("TEMP", labels)
        self.assertIn("FRAME", labels)
        self.assertNotIn("GPU", [item.get("label") for item in hud_rings.items_for(
            {"fps": 90, "real": 45, "target": 90, "tdp": 12}, "detailed")])


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
            self.assertTrue(svc._profile_enabled("game"))
        finally:
            fixture.tearDown()


if __name__ == "__main__":
    unittest.main()
