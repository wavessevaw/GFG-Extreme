"""Governor 2.1.1 field log (Steam Deck, 90 Hz): fixes shipped in 2.1.2."""
import asyncio
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "py_modules")]

from gfg_plugin.autopilot.planner import View, decide  # noqa: E402
from gfg_plugin.governor_confirmation import Request, evaluate_confirmation  # noqa: E402
from gfg_plugin.governor_core import (  # noqa: E402
    BudgetController, OperatingPoint, WindowVerdict, window_verdict,
)
from gfg_plugin.governor_telemetry import TelemetryObserver  # noqa: E402

H = "I MAKO Renderer: present diagnostics: "


def fractional_stream(real, output, *, plan_lines=True, n=30):
    """An adaptive x2.25 stream: interval lines interleaved with integer instant-plan lines."""
    t = {"now": 0.0}
    obs = TelemetryObserver(Path("/nonexistent"), time_fn=lambda: t["now"])
    req = Request(1, OperatingPoint("27x2.25", 60, 27, 2.25, 100), {}, {}, 1, 0.0,
                  obs.event_seq, obs.session_generation, False)
    obs.consume_line(H + "operation=runtime-state-applied role=frame-generation state_revision=2 "
                     "transition=live frame_generation_enabled=1 adaptive=1 target_fps=60 multiplier=2 "
                     "base_fps_cap=27", now=0.1)
    for i in range(n):
        t["now"] = 0.5 + i * 0.5
        if plan_lines and i % 2:
            # the renderer plans 1 or 2 generated frames per real frame for x2.25
            obs.consume_line(H + f"operation=adaptive-plan role=frame-generation base_fps={real} "
                             f"generated={1 + i % 4 // 2}", now=t["now"])
        else:
            obs.consume_line(H + f"operation=adaptive-plan role=frame-generation base_fps={real} "
                             f"target_fps={output} generated=1 source_interval_mean_ms={1000 / real:.3f} "
                             f"requested_interval_mean_ms={1000 / output:.3f}", now=t["now"])
    return req, obs


def confirm(req, obs, now=26.0):
    return evaluate_confirmation(req, obs, now, budget=True, min_samples=8, min_span_s=4.0, timeout_s=25.0)


class FractionalConfirmationTests(unittest.TestCase):
    def test_delivered_x2222_at_60_confirms_despite_integer_plan_samples(self):
        """27x2.25 delivered 2.222 / 60.0 / 26.99 but timed out: x2/x3 plan samples broke the run."""
        req, obs = fractional_stream(26.99, 60.0)
        self.assertEqual(confirm(req, obs), ("confirmed", "event+cadence"))

    def test_a_fractional_point_delivering_x2_still_fails(self):
        req, obs = fractional_stream(30.0, 60.0)
        self.assertEqual(confirm(req, obs), ("failed", "confirmation-timeout"))

    def test_plan_only_stream_keeps_the_old_basis(self):
        t = {"now": 0.0}
        obs = TelemetryObserver(Path("/nonexistent"), time_fn=lambda: t["now"])
        req = Request(1, OperatingPoint("30x3", 90, 30, 3, 100), {}, {}, 1, 0.0,
                      obs.event_seq, obs.session_generation, False)
        for i in range(12):
            t["now"] = 0.5 + i * 0.7
            obs.consume_line(H + "operation=adaptive-plan role=frame-generation base_fps=30 generated=2",
                             now=t["now"])
        self.assertEqual(confirm(req, obs, 6.0)[0], "confirmed")


class OnTargetToleranceTests(unittest.TestCase):
    P = OperatingPoint("30x3", 90, 30, 3, 100)

    def summary(self, real, output):
        return {"real": {"p5": real, "median": real}, "output": {"median": output}, "misses": 0,
                "hard_pressure": 0}

    def test_within_8_percent_of_the_goal_holds(self):
        self.assertTrue(window_verdict(self.summary(28.0, 84.0), self.P).healthy)   # 84 >= 82.8
        self.assertTrue(window_verdict(self.summary(27.7, 83.0), self.P).healthy)
        bad = window_verdict(self.summary(27.0, 81.0), self.P)
        self.assertFalse(bad.healthy)
        self.assertTrue(bad.short)

    def test_no_fast_watts_for_the_last_few_fps(self):
        c = BudgetController(target_output_fps=90, now=0.0)
        c.tdp = 9.0
        for t in (1.0, 2.0, 3.0):
            self.assertEqual(c.fast_check(t, 28.0, 9.0), "hold")
        self.assertEqual(c.fast_check(4.0, 26.0, 9.0), "hold")
        self.assertEqual(c.fast_check(5.0, 26.0, 9.0), "move", "a real shortfall still gets watts")


class PreferX3Tests(unittest.TestCase):
    def test_delivered_real_that_x3_carries_to_the_goal_stays_at_x3(self):
        c = BudgetController(target_output_fps=90, now=0.0)
        c.probe = "up"
        c._move("testing-fewer-generated-frames", idx=c.idx + 1)       # 33x2.75
        c.request_failed(10.0, "delivered-deeper-ratio", {"real": 28.0, "output": 90.0})
        self.assertEqual(c.point.key, "30x3", "28 x 3 = 84 is on target: no x3.25")

    def test_ratios_above_x3_only_after_the_normal_budget(self):
        c = BudgetController(target_output_fps=90, now=0.0, min_tdp_w=3, max_tdp_w=25)
        c.phase, c.tdp, c.draw_w = "locked", 11.0, 11.0
        c.last_good = (c.idx, 11.0)
        seen = []
        for k in range(30):
            c.draw_w = c.tdp
            c.observe(100.0 + 15 * k, WindowVerdict(False, False, "real-below-cap", short=True), 25.0, 75.0)
            seen.append((c.point.key, c.tdp))
        first_deep = next(i for i, (key, _) in enumerate(seen) if key in ("28x3.25", "26x3.5", "24x3.75"))
        self.assertTrue(all(key == "30x3" for key, _ in seen[:first_deep]))
        self.assertEqual(seen[first_deep - 1][1], 15.0, "every normal watt first")
        self.assertEqual(seen[first_deep][0], "26x3.5", "the highest point above x3 that 25 real holds")

    def test_economy_trials_never_go_above_x3(self):
        c = BudgetController(target_output_fps=90, now=0.0, min_tdp_w=3, max_tdp_w=15, minimize_tdp=True)
        c.tdp = 7.0
        self.assertIsNone(c._economy_candidate(10.0), "30x3 is the cheapest cadence up to x3")

    def test_request_fallback_prefers_x3(self):
        c = BudgetController(target_output_fps=90, now=0.0)
        c.request_failed(5.0, "renderer-transition-failed")
        self.assertLessEqual(float(c.point.multiplier), 3.0)


class FullScaleTwinTests(unittest.TestCase):
    def test_refused_scale_keeps_the_cadence_and_rejects_the_rung(self):
        c = BudgetController(target_output_fps=90, now=0.0)
        c.scale_capable = True
        c.idx = next(i for i, p in enumerate(c.points) if p.key == "30x3@80")
        kept = c.keep_full_scale(10.0, "application-extent-override-no-source-presentation-split")
        self.assertEqual(kept.key, "30x3")
        self.assertEqual(c.point.key, "30x3")
        self.assertIn("30x3@80", c.rejected)
        self.assertFalse(c._usable(next(i for i, p in enumerate(c.points) if p.key == "30x3@80"), 20.0))

    def test_no_twin_beyond_the_renderer_capacity(self):
        c = BudgetController(target_output_fps=90, now=0.0)
        c.idx = next(i for i, p in enumerate(c.points) if p.key == "30x3@80")
        c.current_max_multiplier = 2.0
        self.assertIsNone(c.keep_full_scale(10.0, "x"))


def view(**kwargs):
    base = dict(real_fps=None, output_fps=None, frametime_p95_ms=None, target_fps=90, gpu_busy=40,
                cpu_busy=30, gpu_mhz=1200, temp_c=55, draw_w=10, ceiling_w=15, fresh=False, samples=2,
                gpu_clock_available=True)
    base.update(kwargs)
    return View(**base)


class TelemetryMessageTests(unittest.TestCase):
    def test_short_window_after_a_change_is_not_lost_telemetry(self):
        decision = decide(view(settling=True))
        self.assertEqual((decision.action, decision.reason), ("HOLD", "measuring-after-change"))
        self.assertNotIn("Lost reliable telemetry", decision.message)
        self.assertEqual(decide(view()).reason, "telemetry-not-fresh")

    def test_service_marks_a_live_short_baseline_as_settling(self):
        import test_governor_runtime as legacy
        fixture = legacy.RuntimeBase()
        fixture.setUp()
        try:
            svc = fixture.svc
            svc._settings.setdefault("profiles", {}).setdefault("game", {})["enabled"] = True
            svc.set_mode("game", "autopilot")
            svc._active_profile = "game"
            svc.observer.snapshot = lambda: {"available": True, "sample_age_ms": 600}
            asyncio.run(svc._autopilot_tick("game", {"samples": 2, "sample_span_s": 1.0,
                                                     "real": {"median": 30}, "output": {"median": 90}}, 90))
            self.assertEqual(svc._status["autopilot"]["reason"], "measuring-after-change")
            svc.observer.snapshot = lambda: {"available": True, "sample_age_ms": 9000}
            asyncio.run(svc._autopilot_tick("game", {"samples": 0, "sample_span_s": 0.0}, 90))
            self.assertEqual(svc._status["autopilot"]["reason"], "telemetry-not-fresh")
        finally:
            fixture.tearDown()

    def test_tool_in_cooldown_is_not_reported_as_a_skipped_experiment(self):
        import test_governor_runtime as legacy
        from gfg_plugin.autopilot.gpu_clock import GpuClock, MemoryBackend
        fixture = legacy.RuntimeBase()
        fixture.setUp()
        try:
            svc = fixture.svc
            svc._settings.setdefault("profiles", {}).setdefault("game", {})["enabled"] = True
            svc.set_mode("game", "autopilot")
            svc._active_profile = "game"
            svc._menu_covering = lambda: False
            svc._clock = lambda: 50
            svc._autopilot_gpu = GpuClock(backend=MemoryBackend(), writes_enabled=True)
            svc._status["sensors"] = {"cpu_top_core_pct": 95, "gpu_busy_pct": 40, "temp_c": 65,
                                      "gpu_clock_mhz": 1200}
            svc._autopilot_arbiter.cooldown_until = 80
            row = {"samples": 9, "sample_span_s": 9, "first_sample_seq": 11, "last_sample_seq": 20,
                   "real": {"median": 30}, "output": {"median": 90}, "multiplier": {"median": 3},
                   "frametime": {"p95_ms": 33}}
            self.assertFalse(asyncio.run(svc._autopilot_tick("game", row, 90)))
            status = svc._status["autopilot"]
            self.assertNotIn("skipped", status["message"])
            self.assertNotEqual(status["reason"], "cooldown")
            self.assertFalse(svc._autopilot_gpu.owned)
            self.assertFalse(svc._autopilot_blocks_planned(), "the budget keeps running")
        finally:
            fixture.tearDown()


if __name__ == "__main__":
    unittest.main()
