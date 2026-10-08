"""Regression tests for Battery-only savings effort (the hours UI was retired in 1.4.3)."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "py_modules"))

from gfg_plugin.savings_effort import SavingsEffort, hard_refresh_target  # noqa: E402
from gfg_plugin.governor_core import BudgetController  # noqa: E402


class SavingsEffortTests(unittest.TestCase):
    def test_hard_controls_exact_rates_and_only_hard(self):
        for level in ("off", "light", "medium"):
            self.assertIsNone(hard_refresh_target(level, "oled", False))
            self.assertIsNone(hard_refresh_target(level, "lcd", False))
        self.assertEqual(hard_refresh_target("hard", "oled", False), 60)
        self.assertEqual(hard_refresh_target("hard", "lcd", False), 45)
        self.assertIsNone(hard_refresh_target("hard", "oled", True))
        self.assertIsNone(hard_refresh_target("hard", "unknown", False))

    def test_levels_have_safe_bounds_and_off_is_unrestricted(self):
        p = SavingsEffort()
        expected = {"off": None, "light": 14.0, "medium": 12.0, "hard": 11.0}
        for level, cap in expected.items():
            p.configure(level, "Game")
            limits = p.limits(hardware_min_w=6.0, normal_max_w=15.0)
            self.assertEqual(limits["cap_w"], cap)
            self.assertGreaterEqual(limits["minimum_w"], 6.0)
            if level != "off":
                self.assertGreaterEqual(limits["minimum_w"], 9.0)

    def test_recovery_uses_real_fps_not_interpolated_headline(self):
        p = SavingsEffort()
        p.configure("hard", "heavy-game")
        # 10 actual frames plus synthetic frames is unplayable even if output
        # telemetry claims a higher number. Require consecutive fresh evidence.
        for t in (0, 1, 2, 3):
            self.assertFalse(p.observe(t, real_fps=10, output_fps=60, target_fps=60,
                                       tdp_w=11, draw_w=10.5, valid=True, normal_max_w=15))
        self.assertTrue(p.observe(4.1, real_fps=10, output_fps=60, target_fps=60,
                                  tdp_w=11, draw_w=10.5, valid=True, normal_max_w=15))
        limits = p.limits(6, 15)
        self.assertGreaterEqual(limits["minimum_w"], 13)
        self.assertIsNone(limits["cap_w"], "the power-saving ceiling must release on FPS collapse")
        self.assertTrue(limits["quality_limited"])

    def test_missing_or_stale_samples_must_not_change_policy(self):
        p = SavingsEffort()
        p.configure("hard", "game")
        for t in range(15):
            self.assertFalse(p.observe(t, real_fps=10 if t % 2 else None,
                                       output_fps=30, target_fps=60,
                                       tdp_w=11, draw_w=10.8, valid=t % 3 == 0,
                                       normal_max_w=15))
        self.assertIsNone(p.learned_floor_w)
        # A menu / non-binding cap is not a power shortage.
        for t in range(10):
            self.assertFalse(p.observe(t, real_fps=10, output_fps=30,
                                       target_fps=60, tdp_w=11, draw_w=4.5,
                                       valid=True, normal_max_w=15))

    def test_game_switch_resets_unproven_learning(self):
        p = SavingsEffort()
        p.configure("hard", "A", learned_floor_w=13)
        self.assertEqual(p.limits(6, 15)["minimum_w"], 13)
        p.configure("hard", "B")
        self.assertEqual(p.limits(6, 15)["minimum_w"], 9)
        p.configure("hard", "B", learned_floor_w=12)
        self.assertEqual(p.limits(6, 15)["minimum_w"], 12)

    def test_bounded_by_device_capability(self):
        p = SavingsEffort()
        p.configure("hard", "game", learned_floor_w=50)
        limits = p.limits(6, 15)
        self.assertEqual(limits["minimum_w"], 15)
        self.assertIsNone(limits["cap_w"])
        self.assertTrue(limits["quality_limited"])

    def test_no_recovery_when_savings_are_off(self):
        p = SavingsEffort()
        p.configure("off", "heavy")
        for t in range(10):
            self.assertFalse(p.observe(t, real_fps=10, output_fps=30,
                                       target_fps=60, tdp_w=10,
                                       draw_w=10, valid=True, normal_max_w=15))
        self.assertIsNone(p.learned_floor_w)


class ControllerIntegrationTests(unittest.TestCase):
    def test_savings_ceiling_and_playable_floor_are_both_enforced(self):
        ctl = BudgetController(target_output_fps=60, now=0, min_tdp_w=3, max_tdp_w=20)
        ctl.set_savings_limits(level="hard", floor_w=9, cap_w=11)
        self.assertEqual((ctl.min_w, ctl.normal_max_w), (9, 11))
        ctl.tdp = 9
        ctl.set_savings_limits(level="hard", floor_w=13, cap_w=None, quality_limited=True)
        self.assertGreaterEqual(ctl.tdp, 13)
        self.assertEqual(ctl.normal_max_w, 15)
        self.assertTrue(ctl.savings_quality_limited)
        ctl.set_savings_limits(level="off", floor_w=6, cap_w=None)
        self.assertEqual((ctl.min_w, ctl.normal_max_w), (6, 15))

    def test_rescue_never_forces_hw_beyond_normal_max(self):
        ctl = BudgetController(target_output_fps=90, now=0, min_tdp_w=3, max_tdp_w=12)
        ctl.set_savings_limits(level="hard", floor_w=13, cap_w=None, quality_limited=True)
        self.assertLessEqual(ctl.tdp, 12)
        self.assertEqual(ctl.normal_max_w, 12)


if __name__ == "__main__":
    unittest.main()
