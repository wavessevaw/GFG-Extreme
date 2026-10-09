"""Extreme offers the quarter-step grid through fixed x4, with capability checks."""
import unittest
from py_modules.gfg_plugin.governor_core import BudgetController, extreme_points, WindowVerdict
from py_modules.gfg_plugin.governor_overlay import point_deltas
from py_modules.gfg_plugin.config_schema import ConfigurationManager

class ExtremeMultiplierTests(unittest.TestCase):
    def test_deep_quarter_steps_exist_for_deck_refresh_targets(self):
        for target in (60, 90, 120):
            points = extreme_points(target)
            plain = [p for p in points if p.render_scale_pct == 100]
            for mult in (3.25, 3.5, 3.75, 4):
                self.assertTrue(any(p.multiplier == mult for p in plain), (target, mult))
            self.assertTrue(all(1 <= p.multiplier <= 4 for p in points))
            self.assertEqual(len({p.key for p in points}), len(points))
            self.assertEqual(points[0].multiplier, 4)
            self.assertTrue(points[0].degraded)

    def test_overlay_pins_fractional_cadence_and_fixed_x4(self):
        saved = ConfigurationManager.get_defaults()
        for point in extreme_points(90):
            if point.render_scale_pct != 100 or point.multiplier < 3.25:
                continue
            delta = point_deltas(point.to_dict(), saved, scale_capable=False, scale_ready=False)
            self.assertEqual(delta["base_fps_cap"], point.base_target_fps)
            if point.multiplier == 4:
                self.assertFalse(delta["adaptive"])
                self.assertEqual(delta["multiplier"], 4)
            else:
                self.assertTrue(delta["adaptive"])
                self.assertFalse(delta["adaptive_stable_cadence"])
                self.assertFalse(delta["adaptive_auto_base_fps_cap"])
                self.assertEqual(delta["adaptive_max_multiplier"], 4)

    def test_reported_capacity_still_blocks_unavailable_ratios(self):
        ctl = BudgetController(target_output_fps=90, now=0, flavor="extreme", max_tdp_w=15)
        ctl.current_max_multiplier = 3
        for i, p in enumerate(ctl.points):
            if p.multiplier > 3:
                self.assertFalse(ctl._usable(i, 0))
        self.assertEqual(ctl.point.key, "45x2")

    def test_fixed_x4_is_reachable_without_scaling_or_more_watts(self):
        ctl = BudgetController(target_output_fps=90, now=0, flavor="extreme", max_tdp_w=15)
        ctl.current_max_multiplier = 4
        ctl.scale_capable = False
        ctl.idx = next(i for i, p in enumerate(ctl.points) if p.key == "24x3.75")
        result = ctl._escalate(30, WindowVerdict(False, True, "real-below-cap", short=True), 22, 82)
        self.assertEqual(result, "move")
        self.assertEqual(ctl.point.key, "23x4")
        self.assertEqual(ctl.tdp, 15)
