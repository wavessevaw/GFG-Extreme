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

    def draw(self, ctl):
        """APU draw: the whole cap when starved, only what the base needs otherwise."""
        if ctl.tdp is None:
            return None
        cap = self.capacity(ctl.tdp)
        base = ctl.point.base_target_fps
        return ctl.tdp if cap <= base else round(ctl.tdp * base / cap, 2)

    def window(self, ctl):
        cap = self.capacity(ctl.tdp)
        base = ctl.point.base_target_fps
        real = min(cap, base)
        if cap >= base:
            return WindowVerdict(True, False, "holds"), real
        return WindowVerdict(False, cap < 0.85 * base, "real-below-cap",
                             short=True, stall=cap < 0.5 * base), real


def run(ctl, game, now, windows):
    trace = []
    for _ in range(windows):
        now += WINDOW
        verdict, real = game.window(ctl)
        ctl.draw_w = game.draw(ctl)
        ctl.observe(now, verdict, real)
        trace.append((ctl.point.key, ctl.tdp, ctl.phase))
    return now, trace


class BudgetPointsTests(unittest.TestCase):
    def test_ladder_90_cheapest_first_x4_only_as_emergency(self):
        keys = [p.key for p in budget_points(90)]
        self.assertEqual(keys, ["23x3.913", "24x3.75", "26x3.5", "28x3.25", "30x3", "33x2.75", "36x2.5",
                                "40x2.25", "45x2", "51x1.75", "60x1.5", "72x1.25", "native90"])
        # The last resort still lands on the panel rate: 23 x 3.913 = 90, not 22 x 4 = 88.
        last = budget_points(90)[0]
        self.assertAlmostEqual(last.base_target_fps * last.multiplier, 90, places=1)
        self.assertTrue(budget_points(90)[0].degraded)
        self.assertFalse(any(p.degraded for p in budget_points(90)[1:]))

    def test_ladder_60_respects_real_floor(self):
        keys = [p.key for p in budget_points(60)]
        # x4 at 60 Hz would mean 15 real FPS; the last resort stops at 20 real.
        self.assertEqual(keys, ["20x3", "24x2.5", "27x2.25", "30x2", "34x1.75", "40x1.5", "48x1.25", "native60"])

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

    def test_deep_points_are_spent_before_any_watts_above_15(self):
        ctl = BudgetController(target_output_fps=90, now=0.0, min_tdp_w=3, max_tdp_w=25)
        game = Game(1.6)  # heavy: 15 W -> 24 real
        now, trace = run(ctl, game, 0.0, 60)
        self.assertEqual(ctl.point.key, "24x3.75")            # deep point, not more watts
        self.assertLessEqual(max(t[1] for t in trace), 15.0)  # never above the normal budget
        self.assertIsNone(ctl.short_since)

    def test_emergency_watts_only_when_the_deepest_point_keeps_missing_its_cap(self):
        ctl = BudgetController(target_output_fps=90, now=0.0, min_tdp_w=3, max_tdp_w=25)
        game = Game(1.2)  # 15 W -> 18 real: even 23 real cannot be held
        now, trace = run(ctl, game, 0.0, 80)
        self.assertGreater(ctl.tdp, 15.0)
        self.assertLessEqual(ctl.tdp, 20.0)
        first_above = next(i for i, t in enumerate(trace) if t[1] > 15.0)
        self.assertEqual(trace[first_above - 1][0], "23x3.913")

    def test_a_deep_point_holding_its_own_cap_never_buys_emergency_watts(self):
        """The real cadence sits at 23 because the point caps it, not for lack of power."""
        ctl = BudgetController(target_output_fps=90, now=0.0, min_tdp_w=3, max_tdp_w=25)
        ctl.idx, ctl.tdp, ctl.phase = 0, 15.0, "locked"
        now = 0.0
        for _ in range(40):  # ten minutes at 23 real: healthy, just deep
            now += WINDOW
            ctl.observe(now, WindowVerdict(True, False, "holds"), 23)
        self.assertIsNone(ctl.short_since)
        self.assertLessEqual(ctl.tdp, 15.0)

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
        self.assertEqual(stock.point.key, "23x3.913")  # x4 is the only escalation left
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
        now, _ = run(ctl, game, now, int(900 / WINDOW))
        self.assertEqual((ctl.point.key, ctl.tdp), ("45x2", 6.0))

    def test_spare_headroom_goes_to_watts_not_quality(self):
        ctl, game, now = self.locked()
        game.scene = 1.5  # much lighter: 7 W now gives 47 real
        now, _ = run(ctl, game, now, int(ctl.REPROBE_S / WINDOW) + 20)
        self.assertEqual(ctl.tdp, 6.0)

    def test_failed_reprobe_backs_off(self):
        ctl, game, now = self.locked()
        ctl.reprobe_interval = interval = ctl.REPROBE_S
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


class RatchetTests(unittest.TestCase):
    """Regressions for the two review findings: the budget must not creep upwards."""

    def locked_at_the_edge(self, fpw=4.5):
        ctl = BudgetController(target_output_fps=90, now=0.0, min_tdp_w=3, max_tdp_w=20)
        game = Game(fpw)
        now, _ = run(ctl, game, 0.0, 40)
        self.assertEqual(ctl.phase, "locked")
        return ctl, game, now

    def dip(self, ctl, now, *, stall, windows=1):
        """A window the game does not hold: a loading screen (stall) or a heavier scene."""
        base = ctl.point.base_target_fps
        real = base * (0.4 if stall else 0.88)
        for _ in range(windows):
            now += WINDOW
            ctl.observe(now, WindowVerdict(False, True, "real-below-cap", short=True, stall=stall), real)
        return now

    def hold(self, ctl, game, now, minutes):
        now, _ = run(ctl, game, now, int(minutes * 60 / WINDOW))
        return now

    def test_loading_screens_every_few_minutes_never_raise_the_budget(self):
        ctl, game, now = self.locked_at_the_edge()
        start = (ctl.point.key, ctl.tdp)
        for _ in range(12):            # an hour of play, a loading screen every 5 min
            now = self.dip(ctl, now, stall=True)
            now = self.hold(ctl, game, now, 5)
        self.assertEqual((ctl.point.key, ctl.tdp), start)

    def test_three_minute_loading_screen_changes_nothing_and_never_buys_emergency_watts(self):
        ctl, game, now = self.locked_at_the_edge()
        before = (ctl.point.key, ctl.tdp)
        now = self.dip(ctl, now, stall=True, windows=int(120 / WINDOW) - 1)
        self.assertEqual((ctl.point.key, ctl.tdp, ctl.phase), before + ("locked",))
        self.assertIsNone(ctl.short_since)
        now = self.dip(ctl, now, stall=True, windows=int(60 / WINDOW) + 1)  # 3 min in total
        self.assertLessEqual(ctl.tdp, before[1] + 2.0)     # at most one budget step
        self.assertIsNone(ctl.short_since)
        now = self.dip(ctl, now, stall=True, windows=int(120 / WINDOW) - 1)  # still under 5 min
        self.assertLessEqual(ctl.tdp, ctl.normal_max_w)     # never the emergency tier
        now = self.hold(ctl, game, now, 15)
        self.assertEqual((ctl.point.key, ctl.tdp), before)  # and all of it comes back

    def test_a_game_that_really_runs_at_a_third_of_the_cap_still_gets_help(self):
        """Settling at 10 W in a game that can only do 12 real is not a loading screen forever."""
        ctl = BudgetController(target_output_fps=90, now=0.0, min_tdp_w=3, max_tdp_w=20)
        run(ctl, Game(1.2), 0.0, 120)                        # 10 W -> 12 real: stall-looking
        self.assertGreater(ctl.tdp, 10.0)

    def test_what_the_guard_spends_is_given_back_within_minutes(self):
        ctl, game, now = self.locked_at_the_edge()
        before = (ctl.point.key, ctl.tdp)
        now = self.dip(ctl, now, stall=False, windows=2)
        self.assertNotEqual((ctl.point.key, ctl.tdp), before)
        self.assertIsNotNone(ctl.recover)
        now = self.hold(ctl, game, now, 5)
        self.assertEqual(ctl.point.key, before[0])
        self.assertLessEqual(ctl.tdp, before[1])     # given back (a probe may be trying lower)
        self.assertIsNone(ctl.recover)

    def test_repeated_real_dips_oscillate_around_the_edge_instead_of_climbing(self):
        ctl, game, now = self.locked_at_the_edge()
        edge = ctl.tdp
        peak = edge
        for _ in range(15):
            now = self.dip(ctl, now, stall=False, windows=2)
            peak = max(peak, ctl.tdp)
            now = self.hold(ctl, game, now, 4)
        self.assertLessEqual(peak, edge + 4.0)
        self.assertEqual((ctl.point.key, ctl.tdp), ("30x3", edge))

    def test_emergency_watts_are_not_bought_by_a_capped_cadence(self):
        """The old rule (real < 22 FPS) was always true on a deep point."""
        ctl = BudgetController(target_output_fps=60, now=0.0, min_tdp_w=3, max_tdp_w=20)
        ctl.idx, ctl.tdp, ctl.phase = 0, 15.0, "locked"      # 20x3 at 60 Hz: real caps at 20
        now = 0.0
        for _ in range(8):
            now += WINDOW
            ctl.observe(now, WindowVerdict(True, False, "holds"), 20)
        self.assertIsNone(ctl.short_since)
        self.dip(ctl, now, stall=False, windows=2)           # one genuine dip, not 60 s of them
        self.assertLessEqual(ctl.tdp, 15.0)


class FastRaiseTests(unittest.TestCase):
    def locked_at_10(self):
        ctl = BudgetController(target_output_fps=90, now=0.0, min_tdp_w=3, max_tdp_w=20)
        now, _ = run(ctl, Game(3.2), 0.0, 40)            # needs ~10 W for 30 real
        return ctl, now

    def test_after_a_menu_the_working_level_comes_back_in_two_seconds(self):
        ctl, now = self.locked_at_10()
        work = ctl.tdp
        ctl.tdp = 6.0                                     # a pause menu walked it down
        self.assertEqual(ctl.fast_check(now + 1, 12.0, 6.0), "hold")   # one check is not enough
        self.assertEqual(ctl.fast_check(now + 2, 12.0, 6.0), "move")
        self.assertEqual(ctl.tdp, work)
        self.assertEqual(ctl.last_good, (ctl.idx, work))   # a failed probe never reverts below it

    def test_without_history_it_climbs_two_watts_per_three_seconds(self):
        ctl = BudgetController(target_output_fps=90, now=0.0, min_tdp_w=3, max_tdp_w=20)
        ctl.tdp, t = 6.0, 0.0
        for _ in range(12):
            t += 1.0
            ctl.fast_check(t, 20.0, ctl.tdp)
        self.assertEqual(ctl.tdp, 11.0)                   # 6 -> 8 -> 10 -> 11, never past the ideal budget
        self.assertEqual(ctl.point.key, "30x3")           # 12-15 W only after deeper multipliers (slow path)

    def test_loading_screen_with_low_draw_and_a_game_at_its_cap_never_raise(self):
        ctl, now = self.locked_at_10()
        tdp = ctl.tdp
        for i in range(10):
            ctl.fast_check(now + i, 12.0, 4.0)            # collapse, draw far under the cap
            ctl.fast_check(now + 20 + i, 30.0, tdp)       # holds its cap
        self.assertEqual(ctl.tdp, tdp)

    def test_a_failing_lower_power_probe_reverts_within_seconds(self):
        ctl, now = self.locked_at_10()
        tdp = ctl.tdp
        ctl.observe(now + 400, WindowVerdict(True, False, "holds"), 30)   # reprobe: -1 W
        self.assertEqual((ctl.probe, ctl.tdp), ("down", tdp - 1))
        ctl.fast_check(now + 401, 27.0, tdp - 1)
        ctl.fast_check(now + 402, 27.0, tdp - 1)
        self.assertEqual((ctl.probe, ctl.tdp), (None, tdp))

    def test_deck_log_2026_10_06_resume_at_6_watts(self):
        """Real numbers: a menu walked TDP to 6 W; back in game 12-15 real, draw 5.1-6.2 W."""
        ctl, now = self.locked_at_10()
        ctl.tdp, ctl.idx = 6.0, [p.key for p in ctl.points].index("33x2.75")
        for i, (real, draw) in enumerate([(14.29, 5.19), (14.77, 5.14), (14.81, 6.04)]):
            ctl.fast_check(now + i, real, draw)
        self.assertGreater(ctl.tdp, 6.0)          # v0.0.7 sat at 6 W for over 2 minutes here

    def test_shortfall_with_the_cap_not_binding_never_buys_watts(self):
        """Critic's case: 36x2.5 at 9 W, real 30 whatever the watts (CPU), draw 7 W."""
        ctl, now = self.locked_at_10()
        ctl.idx, ctl.tdp = [p.key for p in ctl.points].index("36x2.5"), 9.0
        for i in range(20):
            ctl.fast_check(now + i, 30.0, 7.0)
        self.assertEqual(ctl.tdp, 9.0)

    def test_work_level_is_the_last_level_used_not_the_peak(self):
        ctl = BudgetController(target_output_fps=90, now=0.0, min_tdp_w=3, max_tdp_w=20)
        ctl.held = [(0.0, 11.0), (100.0, 8.0)]
        self.assertEqual(ctl._work_tdp(200.0), 8.0)

    def test_without_a_draw_sensor_probes_stay_rare(self):
        ctl, now = self.locked_at_10()
        ctl.draw_w = None
        self.assertEqual(ctl._probe_delay(), ctl.REPROBE_NO_DRAW_S)

    def test_ignored_cap_disables_the_fast_path(self):
        ctl, now = self.locked_at_10()
        ctl.cap_ignored, tdp = True, ctl.tdp
        for i in range(5):
            ctl.fast_check(now + i, 20.0, 18.0)
        self.assertEqual(ctl.tdp, tdp)


class CapIgnoredTests(unittest.TestCase):
    def test_ignored_cap_holds_quality_at_the_comfort_point(self):
        """If the measured draw shows the cap does not bind, lower watts are fiction: do not buy real frames."""
        ctl = BudgetController(target_output_fps=90, now=0.0, min_tdp_w=3, max_tdp_w=20)
        ctl.cap_ignored = True
        run(ctl, Game(20.0), 0.0, 60)   # every level "holds": the cap is not doing anything
        self.assertEqual(ctl.point.key, "30x3")
        self.assertEqual(ctl.phase, "locked")

    def test_ignored_cap_freezes_the_watt_search_and_the_tier_follows_the_draw(self):
        ctl = BudgetController(target_output_fps=90, now=0.0, min_tdp_w=3, max_tdp_w=20)
        tdp = ctl.tdp
        ctl.cap_ignored, ctl.draw_w = True, 15.2
        run(ctl, Game(20.0), 0.0, 60)
        self.assertEqual(ctl.tdp, tdp)                      # no fictional walk down to 6 W
        ctl.draw_w = 15.2
        self.assertEqual(ctl.status()["tier"], "emergency")  # 15.2 W real draw, not "ideal"


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
        self.assertEqual(budget_tier(10, OperatingPoint("23x3.913", 90, 22, 4, 100, degraded=True)), "emergency")

    def test_effort_follows_watts_in_budget_mode(self):
        point = {"multiplier": 3, "render_scale_pct": 100}
        self.assertEqual(raw_effort(point, 30, tdp_w=9), "easy")
        self.assertEqual(raw_effort(point, 30, tdp_w=13), "medium")
        self.assertEqual(raw_effort(point, 30, tdp_w=17), "hard")
        self.assertEqual(raw_effort({"multiplier": 4}, 22, tdp_w=12), "hard")
        self.assertEqual(raw_effort(point, 30, exhausted=True, tdp_w=20), "nightmare")


if __name__ == "__main__":
    unittest.main()
