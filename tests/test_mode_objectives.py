"""Mode objectives: minimum viable watts, balanced recovery, preserved image."""
import asyncio
import unittest

from test_governor_budget import BudgetController, Game, run, WindowVerdict
from test_governor_core import OperatingPointPlanner
from gfg_plugin.governor_core import TrialLadder
import test_governor_runtime as runtime


class BatteryObjectiveTests(unittest.TestCase):
    def controller(self, **kwargs):
        return BudgetController(target_output_fps=90, now=0, min_tdp_w=3,
                                max_tdp_w=15, minimize_tdp=True, **kwargs)

    def test_lower_cadence_finds_less_power_than_the_comfort_point(self):
        c = self.controller()
        _, trace = run(c, Game(4.5), 0, 30)
        self.assertEqual(c.tdp, 6)
        self.assertGreaterEqual(c.point.base_target_fps, 24)
        self.assertIn(("24x3.75", 6, "search_down"), trace)
        self.assertEqual(c.phase, "locked")

    def test_light_game_reaches_reported_device_minimum(self):
        c = self.controller()
        run(c, Game(10), 0, 35)
        self.assertEqual(c.tdp, 3)
        self.assertGreaterEqual(c.point.base_target_fps, 24)

    def test_capacity_three_stays_at_legal_ratios_and_still_searches_below_six(self):
        c = self.controller()
        c.current_max_multiplier = 3
        _, trace = run(c, Game(10), 0, 35)
        self.assertEqual(c.tdp, 3)
        self.assertFalse(any(key == "24x3.75" for key, _, _ in trace))

    def test_unknown_hardware_minimum_keeps_known_safe_floor(self):
        c = BudgetController(target_output_fps=90, now=0, minimize_tdp=True)
        self.assertEqual(c.min_w, 6)

    def test_failed_economy_trial_restores_known_good_point_and_watts(self):
        c = self.controller()
        c.tdp = 7
        c.phase = "upgrade"
        c.last_good = (c.idx, c.tdp)
        saved = c.last_good
        self.assertEqual(c._upgrade(20), "move")
        self.assertEqual(c.probe, "economy")
        self.assertEqual(c.observe(30, WindowVerdict(False, True, "delivery-misses"), 20, 60), "move")
        self.assertEqual((c.idx, c.tdp), saved)
        self.assertGreater(c.rejected.get("24x3.75", 0), 0)

    def test_ignored_cap_never_claims_an_economy_trial(self):
        c = self.controller()
        c.cap_ignored = True
        self.assertIsNone(c._economy_candidate(10))

    def test_bad_economy_trial_fast_rolls_back_instead_of_buying_watts(self):
        c = self.controller()
        c.tdp = 7
        c.phase = "upgrade"
        c.last_good = (c.idx, c.tdp)
        saved = c.last_good
        c._upgrade(20)
        c.fast_check(21, 15, 7)
        self.assertEqual(c.fast_check(22, 15, 7), "move")
        self.assertEqual((c.idx, c.tdp), saved)


class BalancedObjectiveTests(unittest.TestCase):
    def test_lighter_scene_can_win_quality_after_power_floor_is_reached(self):
        c = BudgetController(target_output_fps=90, now=0, flavor="balanced")
        c.tdp = c.min_w
        c.phase = "locked"
        c.draw_w = c.min_w
        self.assertFalse(c._owed_quality())
        self.assertEqual(c.observe(50, WindowVerdict(True, False, "holds"), 45, 90), "move")
        self.assertEqual(c.probe, "up")
        self.assertGreater(c.point.base_target_fps, 45)
        self.assertEqual(c.tdp, c.min_w)

    def test_balanced_heat_never_buys_a_quality_upgrade(self):
        c = BudgetController(target_output_fps=90, now=0, flavor="balanced")
        c.tdp, c.phase, c.draw_w = c.min_w, "locked", c.min_w
        c.set_thermal("hot", 49)
        self.assertEqual(c.observe(50, WindowVerdict(True, False, "holds"), 45, 90), "hold")
        self.assertEqual(c.point.base_target_fps, 45)


class QualityObjectiveTests(unittest.TestCase):
    def test_low_capacity_does_not_recommend_a_resolution_loss(self):
        d = OperatingPointPlanner().recommend(observed_p5_fps=30, observed_multiplier=1,
                                             target_output_fps=90, preserve_resolution=True)
        self.assertTrue(d.point is None or d.point.render_scale_pct == 100)

    def test_upgrade_is_adjacent_and_respects_failure_cooldown(self):
        ladder = TrialLadder(target_output_fps=90, preserve_resolution=True)
        self.assertEqual(ladder.next_upgrade("45x2", lambda p: None, 0).key, "51x1.75")
        ladder.reject("51x1.75", "bad", until=600)
        self.assertNotEqual(ladder.next_upgrade("45x2", lambda p: None, 300).key, "51x1.75")
        self.assertEqual(ladder.next_upgrade("45x2", lambda p: None, 601).key, "51x1.75")

    def test_native_has_no_quality_upgrade(self):
        ladder = TrialLadder(target_output_fps=90, preserve_resolution=True)
        self.assertIsNone(ladder.next_upgrade("native90", lambda p: None, 1000))


class ServiceObjectiveTests(unittest.TestCase):
    def setUp(self):
        self.fixture = runtime.RuntimeBase()
        self.fixture.setUp()
        self.svc = self.fixture.svc

    def tearDown(self):
        self.fixture.tearDown()

    def test_battery_service_selects_minimum_tdp_goal(self):
        self.svc.set_mode("game", "budget")
        self.fixture.feed(20, 45, 90)
        self.fixture.step()
        self.assertTrue(self.svc._budget.minimize_tdp)
        self.assertEqual(self.svc._budget.min_w, 3)

    def test_quality_service_ladder_excludes_resolution_reduction(self):
        self.fixture.prime_not_matching()
        self.fixture.step()
        self.assertTrue(self.svc._ladder.preserve_resolution)
        self.assertTrue(all(p.render_scale_pct == 100 for p in self.svc._ladder.candidates()))

    def test_quality_recovery_uses_saved_budget_and_retains_rollback_point(self):
        svc = self.svc
        svc._point = {"key": "45x2", "target_output_fps": 90, "base_target_fps": 45,
                      "multiplier": 2, "render_scale_pct": 100}
        svc._point_mode = "applied"
        svc._ladder = TrialLadder(target_output_fps=90, preserve_resolution=True)
        svc.search.status.state = "locked"
        svc._quality_next_probe_at = 300
        self.fixture.t["now"] = 301
        svc.power.claim()
        svc.power.set_tdp_w(7)
        fresh = {"real": {"p5": 45}, "output": {"median": 90}}
        self.assertTrue(asyncio.run(svc._quality_reprobe("game", fresh)))
        self.assertFalse(svc.power.state.owned)
        self.assertEqual(svc._request.point.key, "51x1.75")
        self.assertEqual(svc._point["key"], "45x2")
        asyncio.run(svc._fail_request("game", "real-cadence-below-cap"))
        self.assertEqual(svc._point["key"], "45x2")
        self.assertIsNone(svc._request)

    def test_quality_recovery_does_not_run_on_bad_output_or_heat(self):
        svc = self.svc
        svc._point = {"key": "45x2", "target_output_fps": 90, "base_target_fps": 45,
                      "multiplier": 2, "render_scale_pct": 100}
        svc._point_mode = "applied"
        svc._ladder = TrialLadder(target_output_fps=90, preserve_resolution=True)
        svc.search.status.state = "locked"
        self.fixture.t["now"] = 301
        for output, heat in ((60, 65), (90, 86)):
            svc._quality_next_probe_at = 300
            svc._status["sensors"] = {"temp_c": heat}
            self.assertFalse(asyncio.run(svc._quality_reprobe("game",
                {"real": {"p5": 45}, "output": {"median": output}})))
            self.assertIsNone(svc._request)


if __name__ == "__main__":
    unittest.main()
