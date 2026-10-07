import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "py_modules"))

from gfg_plugin.governor_core import OperatingPointPlanner, PowerSearch


class GovernorPlannerTests(unittest.TestCase):
    def setUp(self):
        self.planner = OperatingPointPlanner()

    def test_native90_requires_native_observation(self):
        decision = self.planner.recommend(external_display=False, observed_p5_fps=95, observed_multiplier=1.0)
        self.assertEqual(decision.point.key, "native90")
        self.assertTrue(decision.proven)

    def test_45x2_is_preferred_over_x3(self):
        decision = self.planner.recommend(external_display=False, observed_p5_fps=48, observed_multiplier=2.0)
        self.assertEqual(decision.point.key, "45x2")
        self.assertEqual(decision.point.multiplier, 2)

    def test_fractional_x15_preferred_when_60_real_fps_is_proven(self):
        decision = self.planner.recommend(external_display=False, observed_p5_fps=64, observed_multiplier=1.5)
        self.assertEqual(decision.point.key, "60x1.5")
        self.assertEqual(decision.point.multiplier, 1.5)
        dock = self.planner.recommend(external_display=True, observed_p5_fps=43, observed_multiplier=1.5)
        self.assertEqual(dock.point.key, "40x1.5")

    def test_x15_not_chosen_without_capacity_falls_back_to_x2(self):
        decision = self.planner.recommend(external_display=False, observed_p5_fps=50, observed_multiplier=2.0)
        self.assertEqual(decision.point.key, "45x2")

    def test_30x3_when_45_not_proven(self):
        decision = self.planner.recommend(external_display=False, observed_p5_fps=33, observed_multiplier=3.0)
        self.assertEqual(decision.point.key, "30x3")

    def test_dock_30x2(self):
        decision = self.planner.recommend(external_display=True, observed_p5_fps=33, observed_multiplier=2.0)
        self.assertEqual(decision.point.key, "30x2")
        self.assertEqual(decision.point.target_output_fps, 60)

    def test_no_automatic_x4_x5_candidates(self):
        multipliers = {point.multiplier for point in self.planner.candidates(external_display=False)}
        self.assertEqual(multipliers, {1, 1.25, 1.5, 1.75, 2, 2.25, 2.5, 2.75, 3})
        self.assertLessEqual(max(multipliers), 3)

    def test_quarter_steps_are_chosen_from_proven_capacity(self):
        cases = ((76, "72x1.25"), (54, "51x1.75"), (43, "40x2.25"), (38, "36x2.5"), (35, "33x2.75"))
        for p5, key in cases:
            decision = self.planner.recommend(external_display=False, observed_p5_fps=p5, observed_multiplier=2.0)
            self.assertEqual(decision.point.key, key, p5)

    def test_cost_model_is_monotonic_in_multiplier(self):
        from gfg_plugin.governor_core import CostModel
        pen = [CostModel.multiplier_penalty(m) for m in OperatingPointPlanner.MULTIPLIER_GRID]
        self.assertEqual(pen, sorted(pen))
        self.assertEqual((pen[0], CostModel.multiplier_penalty(1.5), CostModel.multiplier_penalty(2), CostModel.multiplier_penalty(3)), (0, 0.5, 1, 4))


class GovernorPowerSearchTests(unittest.TestCase):
    def test_coarse_to_fine_then_restore_and_lock(self):
        search = PowerSearch()
        search.begin(current_tdp_w=15, min_tdp_w=3, ceiling_tdp_w=15)
        first = search.evaluate(p5_fps=60, base_target_fps=45)
        self.assertEqual(first["target_tdp_w"], 11)
        second = search.evaluate(p5_fps=55, base_target_fps=45)
        self.assertEqual(second["target_tdp_w"], 9)
        third = search.evaluate(p5_fps=43, base_target_fps=45)
        self.assertEqual(third["target_tdp_w"], 11)
        self.assertEqual(search.status.state, "locked")

    def test_locked_search_gives_watts_back_to_a_heavier_scene(self):
        """Audit 1.0.7: a level found in a light scene stayed for the whole session."""
        search = PowerSearch()
        search.begin(current_tdp_w=15, min_tdp_w=3, ceiling_tdp_w=15)
        for p5 in (80, 80, 80, 80, 80):           # menu: walks down to the minimum and locks
            search.evaluate(p5_fps=p5, base_target_fps=45)
        self.assertEqual((search.status.state, search.status.current_tdp_w), ("locked", 3.0))
        self.assertEqual(search.evaluate(p5_fps=43, base_target_fps=45)["action"], "none")   # one bad window
        raised = search.evaluate(p5_fps=43, base_target_fps=45)
        self.assertEqual((raised["action"], raised["target_tdp_w"]), ("set", 5.0))
        severe = search.evaluate(p5_fps=20, base_target_fps=45)                             # severe: at once
        self.assertEqual((severe["action"], severe["target_tdp_w"]), ("set", 8.0))
        self.assertEqual(search.status.state, "locked")
        self.assertEqual(search.evaluate(p5_fps=46, base_target_fps=45)["action"], "none")

    def test_locked_at_the_ceiling_and_still_short_hands_the_point_back(self):
        search = PowerSearch()
        search.begin(current_tdp_w=15, min_tdp_w=3, ceiling_tdp_w=15)
        search.evaluate(p5_fps=50, base_target_fps=45)                       # 15 -> 14
        search.evaluate(p5_fps=40, base_target_fps=45)                       # fails -> back to 15, locked
        self.assertEqual((search.status.state, search.status.current_tdp_w), ("locked", 15.0))
        search.evaluate(p5_fps=20, base_target_fps=45)          # one hitch, however deep: not yet
        self.assertEqual(search.status.state, "locked")
        search.evaluate(p5_fps=20, base_target_fps=45)
        self.assertEqual(search.status.reason, "point-not-healthy-at-ceiling")

    def test_after_a_raise_the_search_walks_down_again(self):
        """1.0.10: raises only ever went up, so marginal windows ratcheted the cap to the ceiling."""
        search = PowerSearch()
        search.begin(current_tdp_w=15, min_tdp_w=3, ceiling_tdp_w=15)
        for _ in range(5):
            search.evaluate(p5_fps=80, base_target_fps=45)    # walks down to 3 W and locks
        search.evaluate(p5_fps=43, base_target_fps=45)
        self.assertEqual(search.evaluate(p5_fps=43, base_target_fps=45)["target_tdp_w"], 5.0)
        for _ in range(PowerSearch.RESEARCH_GOOD_WINDOWS):
            search.evaluate(p5_fps=50, base_target_fps=45)
        self.assertEqual((search.status.state, search.status.reason), ("optimizing", "re-searching-lower-power"))
        lower = search.evaluate(p5_fps=50, base_target_fps=45)
        self.assertEqual((lower["action"], lower["target_tdp_w"]), ("set", 4.0))
        back = search.evaluate(p5_fps=40, base_target_fps=45)  # 4 W does not hold: back to 5, locked
        self.assertEqual((back["target_tdp_w"], search.status.state), (5.0, "locked"))

    def test_without_a_raise_a_locked_level_stays(self):
        search = PowerSearch()
        search.begin(current_tdp_w=15, min_tdp_w=3, ceiling_tdp_w=15)
        search.evaluate(p5_fps=50, base_target_fps=45)
        search.evaluate(p5_fps=40, base_target_fps=45)          # locked at 15 W, no raise
        for _ in range(20):
            self.assertEqual(search.evaluate(p5_fps=50, base_target_fps=45)["action"], "none")
        self.assertEqual(search.status.state, "locked")

    def test_never_exceeds_user_ceiling_in_guard(self):
        search = PowerSearch()
        search.begin(current_tdp_w=12, min_tdp_w=3, ceiling_tdp_w=12)
        outcome = search.guard_recovery(current_tdp_w=12, ceiling_tdp_w=12, severe=True)
        self.assertEqual(outcome["action"], "hold")
        self.assertEqual(search.status.current_tdp_w, 12)

    def test_unhealthy_at_ceiling_does_not_increase_power(self):
        search = PowerSearch()
        search.begin(current_tdp_w=15, min_tdp_w=3, ceiling_tdp_w=15)
        first = search.evaluate(p5_fps=40, base_target_fps=45, hard_pressure=1)
        self.assertEqual(first["action"], "wait")
        self.assertEqual(search.status.reason, "rechecking-at-ceiling")
        outcome = search.evaluate(p5_fps=40, base_target_fps=45, hard_pressure=1)
        self.assertEqual(outcome["action"], "hold")
        self.assertEqual(search.status.state, "guard")
        self.assertEqual(search.status.current_tdp_w, 15)

    def test_one_bad_window_at_ceiling_does_not_end_the_search(self):
        search = PowerSearch()
        search.begin(current_tdp_w=20, min_tdp_w=3, ceiling_tdp_w=20)
        self.assertEqual(search.evaluate(p5_fps=43, base_target_fps=45, misses=1)["action"], "wait")
        outcome = search.evaluate(p5_fps=45, base_target_fps=45, health_ratio=0.97)
        self.assertEqual(outcome["action"], "set")
        self.assertLess(outcome["target_tdp_w"], 20)


class PredictiveLadderTests(unittest.TestCase):
    def test_native_capacity_skips_infeasible_points_without_rejecting(self):
        from gfg_plugin.governor_core import TrialLadder
        ladder = TrialLadder(target_output_fps=90)
        ladder.observe_native_capacity(50, 1.0)  # 50 fps native: x1..x1.5 need 60+ real fps
        point = ladder.next_point(lambda p: None)
        self.assertGreaterEqual(point.multiplier, 1.5)
        self.assertLessEqual(point.base_target_fps, 50 * ladder.CAPACITY_SLACK)
        self.assertEqual(ladder.rejected, {})
        self.assertIn("native90", ladder.predicted)

    def test_capacity_ignored_while_generation_active(self):
        from gfg_plugin.governor_core import TrialLadder
        ladder = TrialLadder(target_output_fps=90)
        ladder.observe_native_capacity(45, 2.0)
        self.assertIsNone(ladder.native_capacity)
        self.assertEqual(ladder.next_point(lambda p: None).key, "native90")
