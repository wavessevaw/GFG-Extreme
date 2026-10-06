"""Budget mode (v0.0.6): watts first, quality second."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "py_modules"))

from gfg_plugin.governor_core import (  # noqa: E402
    BudgetController, OperatingPoint, WindowVerdict, budget_points, budget_tier, raw_effort, window_verdict,
)

WINDOW = 15.0


class Game:
    """Toy APU: real-frame capacity grows with TDP; ``scene`` scales it."""

    def __init__(self, fps_per_watt=4.5, scene=1.0):
        self.fps_per_watt = fps_per_watt
        self.scene = scene

    def capacity(self, tdp):
        return self.fps_per_watt * tdp * self.scene

    def window(self, ctl):
        cap = self.capacity(ctl.tdp)
        base = ctl.point.base_target_fps
        real = min(cap, base)
        if cap >= base:
            return WindowVerdict(True, False, "holds"), real
        return WindowVerdict(False, cap < 0.85 * base, "real-below-cap"), real


def run(ctl, game, now, windows):
    trace = []
    for _ in range(windows):
        now += WINDOW
        verdict, real = game.window(ctl)
        ctl.observe(now, verdict, real)
        trace.append((ctl.point.key, ctl.tdp, ctl.phase))
    return now, trace


class BudgetPointsTests(unittest.TestCase):
    def test_ladder_90_cheapest_first_x4_only_as_emergency(self):
        keys = [p.key for p in budget_points(90)]
        self.assertEqual(keys, ["22x4", "24x3.75", "26x3.5", "28x3.25", "30x3", "33x2.75", "36x2.5",
                                "40x2.25", "45x2", "51x1.75", "60x1.5", "72x1.25", "native90"])
        self.assertTrue(budget_points(90)[0].degraded)
        self.assertFalse(any(p.degraded for p in budget_points(90)[1:]))

    def test_ladder_60_respects_real_floor(self):
        keys = [p.key for p in budget_points(60)]
        self.assertEqual(keys, ["15x4", "24x2.5", "27x2.25", "30x2", "34x1.75", "40x1.5", "48x1.25", "native60"])

    def test_starts_at_30_real_and_10_watts(self):
        ctl = BudgetController(target_output_fps=90, now=0.0, min_tdp_w=3, max_tdp_w=25)
        self.assertEqual((ctl.point.key, ctl.tdp), ("30x3", 10.0))
        ctl60 = BudgetController(target_output_fps=60, now=0.0)
        self.assertEqual(ctl60.point.key, "30x2")


class BudgetSearchTests(unittest.TestCase):
    def test_finds_lowest_watts_then_fewer_generated_frames(self):
        ctl = BudgetController(target_output_fps=90, now=0.0, min_tdp_w=3, max_tdp_w=25)
        _, trace = run(ctl, Game(4.5), 0.0, 40)
        # 30 real needs 6.67 W -> 7 W; 6 W fails and is never kept; 33x2.75 does not fit at 7 W.
        self.assertEqual((ctl.point.key, ctl.tdp, ctl.phase), ("30x3", 7.0, "locked"))
        self.assertIn(("30x3", 6.0, "search_down"), trace)
        self.assertIn("33x2.75", ctl.rejected)

    def test_light_game_spends_headroom_on_quality_at_minimum_watts(self):
        ctl = BudgetController(target_output_fps=90, now=0.0, min_tdp_w=3, max_tdp_w=25)
        run(ctl, Game(8.0), 0.0, 60)
        # Floor is 6 W (48 real): best point that fits is 45x2.
        self.assertEqual((ctl.tdp, ctl.point.key, ctl.phase), (6.0, "45x2", "locked"))

    def test_one_clean_window_is_not_enough_to_lower_power(self):
        ctl = BudgetController(target_output_fps=90, now=0.0)
        ctl.observe(15.0, WindowVerdict(True, False, "holds"), 30)
        self.assertEqual(ctl.tdp, 10.0)
        ctl.observe(30.0, WindowVerdict(True, False, "holds"), 30)
        self.assertEqual(ctl.tdp, 9.0)

    def test_failed_lower_level_restores_last_good_not_the_edge(self):
        ctl = BudgetController(target_output_fps=90, now=0.0)
        game = Game(3.2)  # 30 real needs 9.4 W
        run(ctl, game, 0.0, 30)
        self.assertEqual(ctl.tdp, 10.0)
        self.assertEqual(ctl.phase, "locked")


class BudgetGuardTests(unittest.TestCase):
    def locked(self, fpw=4.5):
        ctl = BudgetController(target_output_fps=90, now=0.0, min_tdp_w=3, max_tdp_w=25)
        game = Game(fpw)
        now, _ = run(ctl, game, 0.0, 40)
        self.assertEqual(ctl.phase, "locked")
        return ctl, game, now

    def test_guard_works_after_lock_deeper_multiplier_before_watts(self):
        ctl, game, now = self.locked()
        game.scene = 0.85  # heavier scene: 7 W now gives 26.8 real
        now, trace = run(ctl, game, now, 12)
        # Inside the ideal tier a watt comes before real FPS below 30.
        first_change = next(t for t in trace if t[:2] != ("30x3", 7.0))
        self.assertEqual(first_change, ("30x3", 8.0, "guard"))
        self.assertEqual((ctl.point.key, ctl.tdp, ctl.phase), ("30x3", 8.0, "locked"))

    def test_above_ideal_tier_deeper_multiplier_comes_before_watts(self):
        ctl, game, now = self.locked(fpw=2.8)  # 30 real needs 10.7 W -> 11 W
        self.assertEqual((ctl.point.key, ctl.tdp), ("30x3", 11.0))
        game.scene = 0.9
        now, trace = run(ctl, game, now, 12)
        first_change = next(t for t in trace if t[:2] != ("30x3", 11.0))
        self.assertEqual(first_change, ("28x3.25", 11.0, "guard"))

    def test_heavier_scene_at_higher_quality_drops_quality_before_watts(self):
        ctl, game, now = self.locked(fpw=8.0)
        self.assertEqual((ctl.point.key, ctl.tdp), ("45x2", 6.0))
        game.scene = 0.8
        now, trace = run(ctl, game, now, 12)
        first_change = next(t for t in trace if t[:2] != ("45x2", 6.0))
        self.assertEqual(first_change, ("40x2.25", 6.0, "guard"))

    def test_single_mild_bad_window_does_not_trigger_guard(self):
        ctl, game, now = self.locked()
        ctl.observe(now + 15, WindowVerdict(False, False, "delivery-misses"), 30)
        self.assertEqual((ctl.point.key, ctl.tdp, ctl.phase), ("30x3", 7.0, "locked"))

    def test_x4_comes_after_15_watts_and_above_15_only_when_real_stays_low(self):
        ctl = BudgetController(target_output_fps=90, now=0.0, min_tdp_w=3, max_tdp_w=25)
        game = Game(1.5)  # very heavy: 15 W -> 22.5 real
        now, trace = run(ctl, game, 0.0, 60)
        tdps_before_x4 = [t[1] for t in trace if t[0] != "22x4"]
        self.assertLessEqual(max(tdps_before_x4), 15.0)
        self.assertEqual(ctl.point.key, "22x4")
        self.assertLessEqual(ctl.tdp, 15.0)  # x4 at 15 W holds 22 real: no emergency watts

    def test_emergency_watts_when_real_below_22_for_a_minute(self):
        ctl = BudgetController(target_output_fps=90, now=0.0, min_tdp_w=3, max_tdp_w=25)
        game = Game(1.2)  # 15 W -> 18 real
        now, trace = run(ctl, game, 0.0, 80)
        self.assertGreater(ctl.tdp, 15.0)
        self.assertLessEqual(ctl.tdp, 20.0)
        first_above = next(i for i, t in enumerate(trace) if t[1] > 15.0)
        self.assertEqual(trace[first_above - 1][0], "22x4")

    def test_never_above_20_watts(self):
        ctl = BudgetController(target_output_fps=90, now=0.0, min_tdp_w=3, max_tdp_w=30)
        run(ctl, Game(0.5), 0.0, 200)
        self.assertEqual(ctl.tdp, 20.0)
        self.assertTrue(ctl.exhausted)

    def test_device_ceiling_is_the_hardware_maximum_not_20(self):
        """A stock OLED caps at 15 W; this user's Deck allows 20 W."""
        stock = BudgetController(target_output_fps=90, now=0.0, min_tdp_w=3, max_tdp_w=15)
        self.assertEqual((stock.normal_max_w, stock.emergency_max_w), (15.0, 15.0))
        run(stock, Game(0.5), 0.0, 200)
        self.assertEqual(stock.tdp, 15.0)          # never above the hardware maximum
        self.assertEqual(stock.point.key, "22x4")  # x4 is the only escalation left
        self.assertTrue(stock.exhausted)
        wide = BudgetController(target_output_fps=90, now=0.0, min_tdp_w=3, max_tdp_w=20)
        self.assertEqual((wide.normal_max_w, wide.emergency_max_w), (15.0, 20.0))

    def test_low_hardware_maximum_below_the_start_watts(self):
        ctl = BudgetController(target_output_fps=90, now=0.0, min_tdp_w=3, max_tdp_w=8)
        self.assertEqual(ctl.tdp, 8.0)
        self.assertEqual((ctl.ideal_max_w, ctl.normal_max_w, ctl.emergency_max_w), (8.0, 8.0, 8.0))

    def test_reprobe_lowers_power_after_scene_gets_lighter(self):
        ctl, game, now = self.locked()
        game.scene = 0.85
        now, _ = run(ctl, game, now, 20)
        heavy_tdp = ctl.tdp
        game.scene = 1.0
        now, _ = run(ctl, game, now, int(ctl.REPROBE_S / WINDOW) + 30)
        self.assertLess(ctl.tdp, heavy_tdp + 1e-6)
        self.assertEqual(ctl.point.key, "30x3")
        self.assertEqual(ctl.tdp, 7.0)

    def test_quality_given_up_to_a_heavy_scene_is_won_back(self):
        ctl, game, now = self.locked(fpw=8.0)
        game.scene = 0.8
        now, _ = run(ctl, game, now, 12)
        self.assertEqual(ctl.point.key, "36x2.5")
        game.scene = 1.0
        now, _ = run(ctl, game, now, int(ctl.REPROBE_S / WINDOW) * 3)
        self.assertEqual((ctl.point.key, ctl.tdp), ("45x2", 6.0))

    def test_spare_headroom_goes_to_watts_not_quality(self):
        ctl, game, now = self.locked()
        game.scene = 1.5  # much lighter: 7 W now gives 47 real
        now, _ = run(ctl, game, now, int(ctl.REPROBE_S / WINDOW) + 20)
        self.assertEqual(ctl.tdp, 6.0)

    def test_failed_reprobe_backs_off(self):
        ctl, game, now = self.locked()
        interval = ctl.reprobe_interval
        now, _ = run(ctl, game, now, int(interval / WINDOW) + 4)
        self.assertGreater(ctl.reprobe_interval, interval)
        self.assertEqual((ctl.point.key, ctl.tdp), ("30x3", 7.0))

    def test_no_tdp_control_still_picks_points(self):
        ctl = BudgetController(target_output_fps=90, now=0.0, tdp_control=False)
        self.assertIsNone(ctl.tdp)
        for i in range(2):
            ctl.observe(15.0 * (i + 1), WindowVerdict(True, False, "holds"), 30)
        self.assertEqual(ctl.point.key, "33x2.75")

    def test_unconfirmed_point_falls_back_and_is_not_retried_immediately(self):
        ctl = BudgetController(target_output_fps=90, now=0.0)
        for i in range(2):
            ctl.observe(15.0 * (i + 1), WindowVerdict(True, False, "holds"), 30)
        ctl.observe(45.0, WindowVerdict(True, False, "holds"), 30)
        ctl.observe(60.0, WindowVerdict(True, False, "holds"), 30)
        # force an upgrade probe and fail its confirmation
        ctl.phase = "upgrade"
        ctl.good = 1
        ctl.observe(75.0, WindowVerdict(True, False, "holds"), 30)
        self.assertEqual(ctl.point.key, "33x2.75")
        ctl.request_failed(80.0, "confirmation-timeout")
        self.assertEqual(ctl.point.key, "30x3")
        self.assertIn("33x2.75", ctl.rejected)


class VerdictTests(unittest.TestCase):
    P = OperatingPoint("30x3", 90, 30, 3, 100)

    def summary(self, real_p5=30, output=90, misses=0, hard=0, p95=None):
        return {"real": {"p5": real_p5, "median": real_p5}, "output": {"median": output},
                "misses": misses, "hard_pressure": hard, "real_interval_p95_ms": p95}

    def test_holds(self):
        self.assertTrue(window_verdict(self.summary(), self.P).healthy)

    def test_single_threshold_and_pacing(self):
        self.assertFalse(window_verdict(self.summary(real_p5=28), self.P).healthy)
        self.assertTrue(window_verdict(self.summary(real_p5=28.6), self.P).healthy)
        self.assertTrue(window_verdict(self.summary(misses=1), self.P).healthy)
        self.assertFalse(window_verdict(self.summary(misses=2), self.P).healthy)
        self.assertFalse(window_verdict(self.summary(hard=1), self.P).healthy)
        self.assertEqual(window_verdict(self.summary(p95=60.0), self.P).reason, "uneven-pacing")
        self.assertTrue(window_verdict(self.summary(p95=40.0), self.P).healthy)
        self.assertTrue(window_verdict(self.summary(real_p5=20), self.P).severe)


class TierEffortTests(unittest.TestCase):
    def test_tiers(self):
        p = OperatingPoint("30x3", 90, 30, 3, 100)
        self.assertEqual(budget_tier(10, p), "ideal")
        self.assertEqual(budget_tier(14, p), "heavy")
        self.assertEqual(budget_tier(17, p), "emergency")
        self.assertEqual(budget_tier(10, OperatingPoint("22x4", 90, 22, 4, 100, degraded=True)), "emergency")

    def test_effort_follows_watts_in_budget_mode(self):
        point = {"multiplier": 3, "render_scale_pct": 100}
        self.assertEqual(raw_effort(point, 30, tdp_w=9), "easy")
        self.assertEqual(raw_effort(point, 30, tdp_w=13), "medium")
        self.assertEqual(raw_effort(point, 30, tdp_w=17), "hard")
        self.assertEqual(raw_effort({"multiplier": 4}, 22, tdp_w=12), "hard")
        self.assertEqual(raw_effort(point, 30, exhausted=True, tdp_w=20), "nightmare")


if __name__ == "__main__":
    unittest.main()
