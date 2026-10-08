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
        _, trace = run(ctl, game, 0.0, 30)
        # 9 W is only ever a short probe; every settled state is 10 W.
        self.assertTrue(all(tdp == 10.0 for _, tdp, phase in trace if phase == "locked"))
        self.assertEqual(ctl.floor_failures[ctl.idx][0], 9.0)


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
        """A stock Deck caps at 15 W; the ceiling follows the device."""
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
        # 6 W failed three times while locking: it waits out its back-off (draw readings alone do
        # not lift a repeated failure, 1.0.11), then the lighter scene gets it.
        now, _ = run(ctl, game, now, int(ctl.FLOOR_BACKOFF_MAX_S / WINDOW) + 8)
        self.assertEqual(ctl.tdp, 6.0)

    def test_failed_reprobe_backs_off(self):
        ctl, game, now = self.locked()
        ctl.reprobe_interval = interval = ctl.REPROBE_S
        now, trace = run(ctl, game, now, int(interval / WINDOW) + 4)
        # 6 W just failed with this point and the game still draws the whole cap: not retried yet.
        self.assertNotIn(6.0, [tdp for _, tdp, _ in trace])
        self.assertEqual((ctl.point.key, ctl.tdp), ("30x3", 7.0))
        self.assertEqual(ctl.status()["floor_w"], 6.0)

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

    def test_missing_renderer_sample_breaks_consecutive_fast_checks(self):
        ctl = BudgetController(target_output_fps=90, now=0.0, min_tdp_w=3, max_tdp_w=20)
        ctl.tdp = 6.0
        self.assertEqual(ctl.fast_check(1.0, 12.0, 6.0), "hold")
        self.assertEqual(ctl.starved_checks, 1)
        self.assertEqual(ctl.fast_check(2.0, None, None), "hold")
        self.assertEqual(ctl.starved_checks, 0, "telemetry loss must end a starvation run")
        self.assertEqual(ctl.fast_check(3.0, 12.0, 6.0), "hold")
        self.assertEqual(ctl.tdp, 6.0)
        self.assertEqual(ctl.fast_check(4.0, 12.0, 6.0), "move")
        self.assertEqual(ctl.tdp, 8.0)

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


class BalancedModeTests(unittest.TestCase):
    def test_points_never_go_below_30_real_and_start_at_45_real_12_watts(self):
        c = BudgetController(target_output_fps=90, now=0.0, min_tdp_w=3, max_tdp_w=25, flavor="balanced")
        self.assertEqual(min(p.base_target_fps for p in c.points[1:]), 30)
        self.assertEqual((c.point.base_target_fps, c.tdp), (45, 12.0))
        self.assertEqual(c.status()["flavor"], "balanced")

    def test_never_uses_the_last_resort_point_or_emergency_watts(self):
        c = BudgetController(target_output_fps=90, now=0.0, min_tdp_w=3, max_tdp_w=25, flavor="balanced")
        game = Game(0.6)  # hopeless game: nothing holds
        now, trace = run(c, game, 0.0, 400)
        self.assertFalse(any(point == c.points[0].key for point, _, _ in trace))
        self.assertLessEqual(max(t for _, t, _ in trace), 15.0)
        self.assertEqual(min(p for p in (c.point.base_target_fps,)), 30)
        self.assertTrue(c.exhausted)

    def test_oled_balanced_fixed_x2_60_output_recovers_90_without_extra_watts(self):
        """Deck log 2026-10-08: 30 real x2 = 60 output at 8 W / 12 W, goal 90."""
        c = BudgetController(target_output_fps=90, now=0.0, min_tdp_w=3, max_tdp_w=20, flavor="balanced")
        self.assertEqual(c.point.key, "45x2")
        c.phase = "locked"
        c.draw_w = 8.0
        verdict = window_verdict(
            {"real": {"p5": 30.0, "median": 30.0}, "output": {"median": 60.0}},
            c.point,
        )
        self.assertTrue(verdict.short)
        self.assertFalse(verdict.stall)
        self.assertEqual(c.observe(8.0, verdict, 30.0, 60.0), "move")
        self.assertEqual(c.point.key, "30x3")
        self.assertEqual(c.tdp, 12.0, "unused APU headroom cannot repair a 30-FPS game cap")
        self.assertIn("guard-output-recovery", c.last_reason)
        self.assertEqual(c.quality_debt, c.comfort_idx)
        self.assertGreaterEqual(c.point.base_target_fps, 30)

    def test_balanced_keeps_quality_when_output_already_reaches_90(self):
        """Real cadence alone is insufficient evidence: delivered output matters."""
        c = BudgetController(target_output_fps=90, now=0.0, flavor="balanced")
        c.phase, c.draw_w = "locked", 8.0
        verdict = window_verdict(
            {"real": {"p5": 30.0, "median": 30.0}, "output": {"median": 90.0}},
            c.point,
        )
        self.assertEqual(c.observe(8.0, verdict, 30.0, 90.0), "hold")
        self.assertEqual((c.point.key, c.tdp), ("45x2", 12.0))

    def test_balanced_does_not_violate_30_real_floor_or_spend_unused_watts(self):
        """At 26 real there is no legal x3 point that can reliably hold 90."""
        c = BudgetController(target_output_fps=90, now=0.0, flavor="balanced")
        c.phase, c.draw_w = "locked", 8.0
        verdict = window_verdict(
            {"real": {"p5": 26.0, "median": 26.0}, "output": {"median": 52.0}},
            c.point,
        )
        self.assertEqual(c.observe(8.0, verdict, 26.0, 52.0), "hold")
        self.assertEqual((c.point.key, c.tdp), ("45x2", 12.0))
        self.assertIn("guard-not-power-bound", c.last_reason)

    def test_balanced_60hz_does_not_attempt_sub_30_real_recovery(self):
        """60-Hz panels start at the deepest regular Balanced point, 30x2."""
        c = BudgetController(target_output_fps=60, now=0.0, flavor="balanced")
        c.phase, c.draw_w = "locked", 8.0
        verdict = window_verdict(
            {"real": {"p5": 26.0, "median": 26.0}, "output": {"median": 52.0}},
            c.point,
        )
        self.assertEqual(c.observe(8.0, verdict, 26.0, 52.0), "hold")
        self.assertEqual(c.point.key, "30x2")

    def test_battery_flavour_is_unchanged(self):
        c = BudgetController(target_output_fps=90, now=0.0, min_tdp_w=3, max_tdp_w=25)
        self.assertEqual((c.point.base_target_fps, c.tdp, c.flavor), (30, 10.0, "battery"))


class SixtyHertzTests(unittest.TestCase):
    """Steam Deck LCD and docked play (60 FPS target)."""

    def test_battery_and_balanced_start_on_integer_ratios(self):
        b = BudgetController(target_output_fps=60, now=0.0, min_tdp_w=3, max_tdp_w=15)
        self.assertEqual((b.point.key, b.tdp), ("30x2", 10.0))
        m = BudgetController(target_output_fps=60, now=0.0, min_tdp_w=3, max_tdp_w=15, flavor="balanced")
        self.assertEqual((m.point.key, m.tdp), ("30x2", 12.0))
        self.assertTrue(float(m.point.multiplier).is_integer())

    def test_ninety_hertz_starts_are_unchanged(self):
        self.assertEqual(BudgetController(target_output_fps=90, now=0.0).point.key, "30x3")
        self.assertEqual(BudgetController(target_output_fps=90, now=0.0, flavor="balanced").point.key, "45x2")

    def test_balanced_60_never_goes_below_30_real_or_to_the_last_resort(self):
        c = BudgetController(target_output_fps=60, now=0.0, min_tdp_w=3, max_tdp_w=15, flavor="balanced")
        now, trace = run(c, Game(0.8), 0.0, 300)
        self.assertGreaterEqual(min(c.points[i].base_target_fps for i in range(1, len(c.points))), 30)
        self.assertFalse(any(key == c.points[0].key for key, _, _ in trace))
        self.assertLessEqual(max(t for _, t, _ in trace), 15.0)

    def test_capacity_two_still_allows_the_60_hz_last_resort(self):
        c = BudgetController(target_output_fps=60, now=0.0, min_tdp_w=3, max_tdp_w=20)
        c.current_max_multiplier = 3.0
        self.assertTrue(c._usable(0, 0.0))          # 20x3 needs only two generated frames

    def test_a_60_hz_game_that_holds_lowers_power(self):
        c = BudgetController(target_output_fps=60, now=0.0, min_tdp_w=3, max_tdp_w=15)
        now, trace = run(c, Game(4.5), 0.0, 20)
        self.assertLess(c.tdp, 10.0, trace)


class FailureMemoryTests(unittest.TestCase):
    """Field log: 33x2.75 at 10 W tried in three controllers (mode switches)."""

    def test_failed_upgrade_is_reported_and_a_new_controller_skips_it_at_the_same_tdp(self):
        c = BudgetController(target_output_fps=90, now=0.0, min_tdp_w=3, max_tdp_w=20)
        c.idx = next(i for i, p in enumerate(c.points) if p.key == "33x2.75")
        c.tdp, c.probe, c.phase = 10.0, "up", "upgrade"
        c.last_good = (c.idx - 1, 10.0)
        c.request_failed(5.0, "confirmation-timeout", None)
        self.assertEqual(c.new_failures, [("33x2.75", 10.0)])

        fresh = BudgetController(target_output_fps=90, now=100.0, min_tdp_w=3, max_tdp_w=20)
        fresh.load_failures({"33x2.75": (10.0, 0.0)}, 100.0)
        up = next(i for i, p in enumerate(fresh.points) if p.key == "33x2.75")
        fresh.tdp = 10.0
        self.assertFalse(fresh._upgrade_allowed(up, 100.0))
        fresh.tdp = 11.0
        self.assertTrue(fresh._upgrade_allowed(up, 100.0), "more watts: worth trying again")
        fresh.tdp = 10.0
        self.assertTrue(fresh._upgrade_allowed(up, 100.0 + fresh.FAILURE_TTL_S), "a lighter scene later")


class GeneratedCapacityLimitTests(unittest.TestCase):
    """Field log: 28x3.25 / 26x3.5 / 24x3.75 became a fixed x3 at 84/78/72 FPS."""

    def test_points_beyond_capacity_are_never_used_and_the_guard_buys_watts_instead(self):
        c = BudgetController(target_output_fps=90, now=0.0, min_tdp_w=3, max_tdp_w=20)
        c.current_max_multiplier = 3.0
        c.idx = next(i for i, p in enumerate(c.points) if p.key == "30x3")
        c.tdp = 11.0
        c.phase = "locked"
        bad = WindowVerdict(False, True, "real-below-cap", short=True)
        c.observe(10.0, bad, 22.8)
        self.assertEqual(c.point.key, "30x3", c.last_reason)
        self.assertGreater(c.tdp, 11.0)
        self.assertFalse(any(c._usable(i, 10.0) for i, p in enumerate(c.points) if p.multiplier > 3))

    def test_a_raised_capacity_after_swapchain_recreation_brings_deeper_ratios_back(self):
        """PR #37 review: capacity is the current swapchain's, not a permanent device limit."""
        c = BudgetController(target_output_fps=90, now=0.0, min_tdp_w=3, max_tdp_w=20)
        deep = [i for i, p in enumerate(c.points) if 3 < p.multiplier < 4]
        c.current_max_multiplier = 3.0
        self.assertFalse(any(c._usable(i, 0.0) for i in deep))
        c.current_max_multiplier = 4.0          # later report: generated_frame_capacity=3
        self.assertTrue(all(c._usable(i, 0.0) for i in deep))
        c.current_max_multiplier = 1.0          # capacity 0: native only
        self.assertEqual([p.multiplier for i, p in enumerate(c.points) if c._usable(i, 0.0)], [1])

    def test_unknown_capacity_keeps_the_old_behaviour(self):
        c = BudgetController(target_output_fps=90, now=0.0)
        self.assertIsNone(c.current_max_multiplier)
        self.assertTrue(any(c._usable(i, 0.0) for i, p in enumerate(c.points) if 3 < p.multiplier < 4))


class TransientGeneratedCapacityTests(unittest.TestCase):
    """Resource slots (swapchain) are temporary, not evidence of failed FPS."""

    def controller(self):
        return BudgetController(target_output_fps=90, now=0.0,
                                min_tdp_w=3, max_tdp_w=20)

    def test_x3_to_x2_and_back_retries_original_point_without_blacklist(self):
        ctl = self.controller()
        self.assertEqual(ctl.point.key, "30x3")
        ctl.current_max_multiplier = 2.0
        self.assertEqual(ctl.adapt_to_capacity(1.0), "move")
        self.assertEqual(ctl.point.key, "45x2")
        self.assertEqual(ctl.status()["capacity_resume_point"], "30x3")
        self.assertEqual(ctl.request_failures, 0)
        self.assertFalse(ctl.rejected)
        self.assertEqual(ctl.new_failures, [])
        self.assertEqual(ctl.adapt_to_capacity(2.0), "hold", "stable limit cannot exhaust us")
        self.assertEqual(ctl.request_failures, 0)
        ctl.current_max_multiplier = 3.0
        self.assertEqual(ctl.adapt_to_capacity(3.0), "hold", "don't flap immediately")
        self.assertEqual(ctl.adapt_to_capacity(5.1), "move")
        self.assertEqual(ctl.point.key, "30x3")
        self.assertEqual(ctl.phase, "settle", "must confirm the live renderer again")
        self.assertIsNone(ctl.status()["capacity_resume_point"])
        self.assertFalse(ctl.rejected)
        self.assertEqual(ctl.request_failures, 0)

    def test_capacity_recovery_must_be_stable_for_two_seconds(self):
        ctl = self.controller()
        ctl.current_max_multiplier = 2.0
        ctl.adapt_to_capacity(1.0)
        ctl.current_max_multiplier = 3.0
        ctl.adapt_to_capacity(2.0)
        ctl.current_max_multiplier = 2.0
        self.assertEqual(ctl.adapt_to_capacity(3.0), "hold")
        ctl.current_max_multiplier = 3.0
        self.assertEqual(ctl.adapt_to_capacity(4.0), "hold")
        self.assertEqual(ctl.adapt_to_capacity(5.0), "hold")
        self.assertEqual(ctl.adapt_to_capacity(6.1), "move")
        self.assertEqual(ctl.point.key, "30x3")

    def test_capacity_restoration_cannot_override_real_tdp_failure_backoff(self):
        ctl = self.controller()
        ctl.current_max_multiplier = 2.0
        ctl.adapt_to_capacity(1.0)
        failed = ctl.points[ctl._capacity_resume_idx]
        ctl.known_failures[failed.key] = (ctl.tdp, 2.0)
        ctl.current_max_multiplier = 3.0
        self.assertEqual(ctl.adapt_to_capacity(3.0), "hold")
        self.assertEqual(ctl.adapt_to_capacity(6.0), "hold", "real failure remains in force")
        self.assertEqual(ctl.point.key, "45x2")
        self.assertFalse(ctl.rejected)
        self.assertEqual(ctl.adapt_to_capacity(603.0), "hold")
        self.assertEqual(ctl.adapt_to_capacity(605.1), "move")
        self.assertEqual(ctl.point.key, failed.key)

    def test_initial_and_remembered_points_respect_current_swapchain(self):
        ctl = self.controller()
        ctl.current_max_multiplier = 2.0
        self.assertFalse(ctl.warm_start("30x3", 8.0, 1.0))
        self.assertEqual(ctl.adapt_to_capacity(1.0), "move")
        self.assertEqual(ctl.point.key, "45x2")
        self.assertEqual(ctl.request_failures, 0)
        remembered = self.controller()
        remembered.current_max_multiplier = 2.0
        self.assertTrue(remembered.warm_start("45x2", 9.0, 1.0))
        self.assertEqual(remembered.point.key, "45x2")

    def test_genuine_failed_point_remains_rejected_after_capacity_returns(self):
        ctl = self.controller()
        ctl.probe = "up"
        ctl._move("test", idx=ctl.idx + 1)
        failed = ctl.point.key
        ctl.request_failed(1.0, "confirmation-timeout")
        self.assertIn(failed, ctl.rejected)
        ctl.current_max_multiplier = 2.0
        ctl.adapt_to_capacity(2.0)
        ctl.current_max_multiplier = 3.0
        ctl.adapt_to_capacity(3.0)
        ctl.adapt_to_capacity(5.1)
        self.assertIn(failed, ctl.rejected, "real renderer failures still use TTL")


class FieldLogTests(unittest.TestCase):
    """Balanced mode, from a field log."""

    def balanced(self):
        return BudgetController(target_output_fps=90, now=0.0, min_tdp_w=3, max_tdp_w=20, flavor="balanced")

    def key(self, c, base):
        return next(i for i, p in enumerate(c.points) if p.base_target_fps == base and i > 0)

    def test_renderer_delivering_x3_instead_of_x2_25_moves_to_30x3(self):
        c = self.balanced()
        c.idx = self.key(c, 40)            # requested 40x2.25 while the GPU could feed only ~30 real
        c.phase = "guard"
        c.request_failed(100.0, "confirmation-timeout", {"real": 30.04, "output": 90.11})
        self.assertEqual(c.point.base_target_fps, 30)
        self.assertEqual(c.point.multiplier, 3)
        self.assertIn("request-failed-use-delivered", c.last_reason)

    def test_delivered_point_is_only_a_candidate_until_fresh_windows_hold(self):
        """PR #35 review: two medians are an observation; fresh windows verify the point."""
        c = self.balanced()
        c.idx = self.key(c, 40)
        c.phase = "guard"
        c.tdp = 13.0
        c.last_good = None
        c.request_failed(100.0, "confirmation-timeout", {"real": 30.0, "output": 90.0})
        self.assertEqual(c.status()["verifying"], c.point.key)
        self.assertIsNone(c.last_good)                         # not a held point yet
        good = WindowVerdict(True, False, "holds")
        c.observe(110.0, good, 30.0)
        self.assertIsNone(c.last_good)                         # one window is not enough
        self.assertEqual(c.status()["verifying"], c.point.key)
        c.observe(118.0, good, 30.0)
        self.assertEqual(c.last_good[0], c.idx)                # HEALTHY_WINDOWS fresh windows
        self.assertIsNone(c.status()["verifying"])

    def test_delivered_point_that_fails_its_windows_is_guarded_normally(self):
        c = self.balanced()
        c.idx = self.key(c, 40)
        c.phase = "guard"
        c.tdp = 13.0
        c.request_failed(100.0, "confirmation-timeout", {"real": 30.0, "output": 90.0})
        point, tdp = c.point.key, c.tdp
        severe = WindowVerdict(False, True, "real-below-cap", short=True)
        self.assertEqual(c.observe(110.0, severe, 22.0), "move")
        self.assertNotEqual((c.point.key, c.tdp), (point, tdp))   # escalated, not kept

    def test_verifying_is_cleared_when_the_guard_leaves_the_inferred_point(self):
        """PR #36/#37 review: failed verification -> move to another point -> verifying is None."""
        c = self.balanced()
        c.idx = self.key(c, 40)
        c.phase = "guard"
        c.tdp = 13.0
        c.request_failed(100.0, "confirmation-timeout", {"real": 33.0, "output": 90.0})
        inferred = c.point.key
        self.assertEqual(c.verifying, inferred)
        severe = WindowVerdict(False, True, "real-below-cap", short=True)
        for t in range(110, 400, 10):
            c.observe(float(t), severe, 20.0)
            if c.point.key != inferred:
                break
        self.assertNotEqual(c.point.key, inferred)
        self.assertIsNone(c.verifying)
        self.assertIsNone(c.status()["verifying"])

    def test_a_tdp_only_move_keeps_verification_of_the_same_point(self):
        c = self.balanced()
        c.idx = self.key(c, 40)
        c.phase = "guard"
        c.tdp = 11.0
        c.request_failed(100.0, "confirmation-timeout", {"real": 30.0, "output": 90.0})
        c.current_max_multiplier = 3.0                       # nothing deeper than x3
        inferred = c.point.key
        c._move("guard-more-power:test", tdp=12.0)
        self.assertEqual((c.point.key, c.verifying), (inferred, inferred))

    def test_short_output_is_still_a_failure(self):
        c = self.balanced()
        c.idx = self.key(c, 40)
        before = c.idx
        c.request_failed(100.0, "confirmation-timeout", {"real": 30.0, "output": 60.0})
        self.assertNotIn("use-delivered", c.last_reason)
        self.assertIn(c.points[before].key, c.rejected)

    def test_guard_skips_a_rejected_neighbour_instead_of_buying_watts(self):
        c = self.balanced()
        c.idx = self.key(c, 45)
        c.tdp = 13.0
        c.phase = "locked"
        c.rejected[c.points[self.key(c, 40)].key] = 50.0   # 40x2.25 rejected a moment ago
        bad = WindowVerdict(False, True, "real-below-cap", short=True)
        c.observe(60.0, bad, 27.0)
        self.assertLess(c.point.base_target_fps, 40, (c.point.key, c.tdp, c.last_reason))
        self.assertEqual(c.tdp, 13.0)


if __name__ == "__main__":
    unittest.main()


class ThermalTests(unittest.TestCase):
    """1.0.4: while the APU heats up, no probe towards more real frames (more watts, more heat)."""

    def test_heating_holds_quality_but_still_lowers_watts(self):
        ctl = BudgetController(target_output_fps=90, now=0.0, min_tdp_w=3, max_tdp_w=25)
        ctl.thermal = "heating"
        _, trace = run(ctl, Game(8.0), 0.0, 60)
        # Watts still go down to the floor; the point stays at 30x3 instead of 45x2.
        self.assertEqual(ctl.tdp, 6.0)
        self.assertEqual(ctl.point.key, "30x3")
        self.assertTrue(ctl.thermal_deferred)
        self.assertTrue(ctl.last_reason.startswith("thermal-quality-held"))
        self.assertFalse(any(key != "30x3" for key, _, _ in trace))

    def test_deferred_quality_is_won_back_after_cooling(self):
        ctl = BudgetController(target_output_fps=90, now=0.0, min_tdp_w=3, max_tdp_w=25)
        ctl.thermal = "hot"
        now, _ = run(ctl, Game(8.0), 0.0, 40)
        self.assertEqual(ctl.point.key, "30x3")
        ctl.thermal = "ok"
        run(ctl, Game(8.0), now, 80)
        self.assertEqual((ctl.tdp, ctl.point.key), (6.0, "45x2"))
        self.assertFalse(ctl.thermal_deferred)

    def test_unknown_thermal_changes_nothing(self):
        a = BudgetController(target_output_fps=90, now=0.0, min_tdp_w=3, max_tdp_w=25)
        b = BudgetController(target_output_fps=90, now=0.0, min_tdp_w=3, max_tdp_w=25)
        b.thermal = "unknown"
        a.thermal = "ok"
        _, ta = run(a, Game(8.0), 0.0, 60)
        _, tb = run(b, Game(8.0), 0.0, 60)
        self.assertEqual(ta, tb)

    def test_heat_verdict_has_hysteresis(self):
        ctl = BudgetController(target_output_fps=90, now=0.0)
        ctl.set_thermal("heating", 100.0)
        ctl._now = 150.0
        ctl.set_thermal("ok", 150.0)
        self.assertTrue(ctl.heat_limited, "a flip to ok does not release quality at once")
        ctl._now = 100.0 + ctl.THERMAL_CLEAR_S + 1
        self.assertFalse(ctl.heat_limited)
        self.assertFalse(ctl.status()["heat_limited"])

    def test_status_reports_thermal(self):
        ctl = BudgetController(target_output_fps=90, now=0.0)
        ctl.thermal = "hot"
        self.assertEqual(ctl.status()["thermal"], "hot")
        self.assertIn("thermal_deferred", ctl.status())


class FloorMemoryTests(unittest.TestCase):
    """Field log: after each guard raise the walk back down probed 9 W again, which
    had just failed; nine visible dips in 29 minutes at the same level."""

    def simulate(self):
        ctl = BudgetController(target_output_fps=90, now=0.0)
        game, now, failed_down = Game(3.0), 0.0, 0   # 30 real needs 10 W
        for i in range(1800 // int(WINDOW)):
            game.scene = 0.85 if i % 10 in (6, 7) else 1.0   # a heavier scene every 150 s
            now += WINDOW
            was = ctl.probe
            verdict, real = game.window(ctl)
            ctl.draw_w = game.draw(ctl)
            ctl.observe(now, verdict, real)
            failed_down += was == "down" and ctl.last_reason.startswith("probe-failed")
        return ctl, failed_down

    def test_heavy_scenes_do_not_restart_failed_power_probes(self):
        ctl, failed = self.simulate()
        self.assertLessEqual(failed, 4)   # 12 before 1.0.5
        self.assertEqual(ctl.point.key, "30x3")

    def test_backoff_doubles_per_repeat_and_is_capped(self):
        ctl = BudgetController(target_output_fps=90, now=0.0)
        self.assertEqual([ctl._floor_backoff(n) for n in (1, 2, 3, 4, 9)], [120.0, 240.0, 480.0, 600.0, 600.0])

    def test_lighter_scene_lifts_the_block(self):
        ctl = BudgetController(target_output_fps=90, now=0.0)
        ctl.floor_failures[ctl.idx] = (9.0, 0.0, 1)
        ctl.draw_w = 9.6
        self.assertTrue(ctl._floor_blocked(9.0, 60.0))
        ctl.draw_w = 7.0   # the game uses clearly less than 9 W now
        self.assertFalse(ctl._floor_blocked(9.0, 60.0))
        ctl.draw_w = None
        self.assertFalse(ctl._floor_blocked(9.0, 600.0), "expired")
        self.assertFalse(ctl._floor_blocked(10.0 + 0.5, 60.0), "a higher level is not blocked")
        ctl.floor_failures[ctl.idx] = (9.0, 0.0, 3)
        ctl.draw_w = 7.0
        self.assertTrue(ctl._floor_blocked(9.0, 60.0), "a repeated failure needs its back-off")

    def test_a_level_that_holds_clears_its_failure(self):
        ctl = BudgetController(target_output_fps=90, now=0.0, min_tdp_w=3, max_tdp_w=25)
        run(ctl, Game(4.5), 0.0, 40)                 # 6 W failed, 7 W holds
        self.assertIn(ctl.idx, ctl.floor_failures)
        game = Game(4.5, scene=1.5)
        run(ctl, game, 600.0, int(ctl.FLOOR_BACKOFF_MAX_S / WINDOW) + 8)
        self.assertEqual(ctl.tdp, 6.0)
        self.assertNotIn(ctl.idx, ctl.floor_failures)


class RequestFallbackTests(unittest.TestCase):
    """Audit 1.0.7: after 'use what was delivered' failed too, the fallback was the rejected point."""

    def test_second_failure_falls_back_to_the_live_point(self):
        ctl = BudgetController(target_output_fps=90, now=0.0)
        live = ctl.point.key                                   # 30x3, confirmed
        ctl.probe = "up"
        ctl._move("testing-fewer-generated-frames", idx=ctl.idx + 1)
        failed = ctl.point.key                                 # 33x2.75
        ctl.request_failed(10.0, "delivered-deeper-ratio", {"real": 28.0, "output": 90.0})
        self.assertEqual(ctl.point.key, "28x3.25")
        ctl.request_failed(40.0, "confirmation-timeout")
        self.assertEqual(ctl.point.key, live)
        self.assertNotEqual(ctl.point.key, failed)

    def test_fallback_never_returns_to_a_point_beyond_the_renderer_capacity(self):
        ctl = BudgetController(target_output_fps=90, now=0.0)
        ctl._move("x", idx=ctl.idx - 1)                        # 28x3.25 requested, prev 30x3
        ctl._move("y", idx=ctl.idx - 1)                        # 26x3.5 requested, prev 28x3.25
        ctl.current_max_multiplier = 3.0
        ctl.request_failed(5.0, "renderer-generated-capacity")
        self.assertLessEqual(float(ctl.point.multiplier), 3.0)


class NotPowerBoundTests(unittest.TestCase):
    """1.0.11 field log: the guard climbed to 15 W while the APU drew 5-11 W."""

    def test_short_window_with_low_draw_buys_no_watts(self):
        ctl = BudgetController(target_output_fps=90, now=0.0)
        ctl.phase, ctl.tdp, ctl.draw_w = "locked", 11.0, 7.0
        ctl.observe(15.0, WindowVerdict(False, False, "real-below-cap", short=True), 29.0)
        ctl.observe(30.0, WindowVerdict(False, False, "real-below-cap", short=True), 29.0)
        self.assertEqual(ctl.tdp, 11.0)
        self.assertTrue(ctl.last_reason.startswith("guard-not-power-bound"))

    def test_binding_draw_still_gets_watts(self):
        ctl = BudgetController(target_output_fps=90, now=0.0)
        ctl.phase, ctl.tdp, ctl.draw_w = "locked", 10.0, 9.8
        ctl.observe(15.0, WindowVerdict(False, False, "real-below-cap", short=True), 29.0)
        ctl.observe(30.0, WindowVerdict(False, False, "real-below-cap", short=True), 29.0)
        self.assertEqual(ctl.tdp, 11.0)

    def test_without_a_draw_sensor_nothing_changes(self):
        ctl = BudgetController(target_output_fps=90, now=0.0)
        ctl.phase, ctl.tdp, ctl.draw_w = "locked", 10.0, None
        ctl.observe(15.0, WindowVerdict(False, False, "real-below-cap", short=True), 29.0)
        ctl.observe(30.0, WindowVerdict(False, False, "real-below-cap", short=True), 29.0)
        self.assertEqual(ctl.tdp, 11.0)


class RenderScaleTests(unittest.TestCase):
    """1.1.0: Battery/Balanced lower the render resolution before deeper ratios and 12-15 W."""

    def heavy(self, capable, windows=2):
        ctl = BudgetController(target_output_fps=90, now=0.0)
        ctl.scale_capable = capable
        ctl.current_max_multiplier = 3.0          # the renderer cannot go deeper than x3
        ctl.phase, ctl.tdp, ctl.draw_w = "locked", 11.0, 10.8
        now = 0.0
        for _ in range(windows):
            now += 15.0
            ctl.observe(now, WindowVerdict(False, False, "real-below-cap", short=True), 28.5)
        return ctl

    def test_ladder_has_scaled_rungs_below_30x3(self):
        keys = [p.key for p in BudgetController(target_output_fps=90, now=0.0).points]
        i = keys.index("30x3")
        self.assertEqual(keys[i - 2:i + 1], ["30x3@80", "30x3@90", "30x3"])
        self.assertEqual(BudgetController(target_output_fps=90, now=0.0).point.key, "30x3")

    def test_heavy_scene_gets_lower_resolution_before_more_watts(self):
        ctl = self.heavy(True)
        self.assertEqual((ctl.point.key, ctl.tdp), ("30x3@90", 11.0))
        ctl = self.heavy(True, windows=3)
        self.assertEqual((ctl.point.key, ctl.tdp), ("30x3@80", 11.0))
        ctl = self.heavy(True, windows=4)                 # only then watts
        self.assertEqual((ctl.point.key, ctl.tdp), ("30x3@80", 12.0))

    def test_without_the_scaling_engine_nothing_changes(self):
        ctl = self.heavy(False)
        self.assertEqual(ctl.point.key, "30x3")
        self.assertGreater(ctl.tdp, 11.0)

    def test_full_resolution_is_won_back_first(self):
        ctl = BudgetController(target_output_fps=90, now=0.0)
        ctl.scale_capable = True
        ctl.idx = [p.key for p in ctl.points].index("30x3@90")
        ctl.phase = "upgrade"
        ctl._upgrade(0.0)
        self.assertEqual(ctl.point.key, "30x3")

    def test_scaled_memory_is_not_used_when_the_launch_cannot_scale(self):
        ctl = BudgetController(target_output_fps=90, now=0.0)
        self.assertFalse(ctl.warm_start("30x3@90", 10.0, 0.0))
        ctl.scale_capable = True
        self.assertTrue(ctl.warm_start("30x3@90", 10.0, 0.0))


class ExtremeTests(unittest.TestCase):
    """Extreme (1.6): the most real frames at the full normal budget, resolution as the currency."""

    def make(self, scale=True, max_w=15.0):
        from gfg_plugin.governor_core import BudgetController
        ctl = BudgetController(target_output_fps=90, now=0.0, min_tdp_w=3.0, max_tdp_w=max_w, flavor="extreme")
        ctl.scale_capable = scale
        return ctl

    def test_ladder_trades_resolution_for_real_frames(self):
        from gfg_plugin.governor_core import extreme_points
        keys = [p.key for p in extreme_points(90)]
        self.assertEqual(keys[0], "23x3.913", "index 0 stays the (unused) last resort")
        i = keys.index
        self.assertLess(i("30x3"), i("33x2.75@80"))
        self.assertLess(i("45x2@80"), i("45x2@90"))
        self.assertLess(i("45x2@90"), i("45x2"))
        self.assertLess(i("45x2"), i("51x1.75@80"))
        self.assertEqual(keys[-1], "native90")
        self.assertNotIn("24x3.75", keys, "never below 30 real")

    def test_starts_at_45_real_on_the_full_budget_and_never_searches_watts_down(self):
        ctl = self.make()
        self.assertEqual((ctl.point.key, ctl.tdp), ("45x2", 15.0))
        game = Game(fps_per_watt=4.0)        # 60 real at 15 W
        _, trace = run(ctl, game, 0.0, 30)
        self.assertTrue(all(t[1] == 15.0 for t in trace), "no lower-power probes in Extreme")
        self.assertGreaterEqual(ctl.point.base_target_fps, 51, "headroom became more real frames")
        self.assertEqual(ctl.flavor, "extreme")

    def test_without_the_scaling_engine_the_plain_ladder_is_used(self):
        ctl = self.make(scale=False)
        game = Game(fps_per_watt=4.0)
        _, trace = run(ctl, game, 0.0, 30)
        self.assertTrue(all("@" not in t[0] for t in trace))

    def test_heavy_scene_gives_up_resolution_before_real_frames(self):
        ctl = self.make()
        game = Game(fps_per_watt=4.0)
        now, _ = run(ctl, game, 0.0, 6)
        game.scene = 0.7                     # 42 real at 15 W: 45x2 no longer holds
        now, trace = run(ctl, game, now, 6)
        keys = [t[0] for t in trace]
        self.assertTrue(any(k.endswith("@90") or k.endswith("@80") for k in keys),
                        f"a lower render scale came before fewer real frames: {keys}")

    def test_a_lower_ceiling_is_the_whole_budget(self):
        ctl = self.make(max_w=12.0)          # the player's own 12 W: never raised to 15
        self.assertEqual((ctl.tdp, ctl.normal_max_w, ctl.emergency_max_w), (12.0, 12.0, 12.0))
        game = Game(fps_per_watt=4.0)
        _, trace = run(ctl, game, 0.0, 30)
        self.assertLessEqual(max(t[1] for t in trace), 12.0)
        ctl.limit_power(9.0)                 # lowered in Quick Access mid-game
        self.assertEqual((ctl.tdp, ctl.normal_max_w), (9.0, 9.0))
        _, trace = run(ctl, game, 400.0, 20)
        self.assertLessEqual(max(t[1] for t in trace), 9.0)

    def test_no_last_resort_ratio(self):
        ctl = self.make()
        game = Game(fps_per_watt=1.0)        # hopeless: 15 real at 15 W
        _, trace = run(ctl, game, 0.0, 40)
        self.assertNotIn("23x3.913", [t[0] for t in trace])
        self.assertGreaterEqual(min(BudgetController.EMERGENCY_CEILING_W, 15.0), max(t[1] for t in trace))
