"""Regression tests for the 2.1.4 Autopilot display-goal policy."""
import sys
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "py_modules")]
from gfg_plugin.autopilot.planner import TargetPolicy

class AutopilotGoalTests(unittest.TestCase):
    def test_auto_does_not_halve_90_when_real_dips_but_output_still_near_goal(self):
        policy = TargetPolicy()
        for seq in (10, 20, 30, 40):
            self.assertEqual(policy.update(90, 26.76, 80.28, "auto", True,
                sample_seq=seq, first_sample_seq=seq-9, span_s=3.0, now=float(seq)), 90)

    def test_auto_does_not_halve_90_even_when_output_short(self):
        policy = TargetPolicy()
        for seq in (10, 20, 30, 40):
            self.assertEqual(policy.update(90, 25.0, 70.0, "auto", True,
                sample_seq=seq, first_sample_seq=seq-9, span_s=3.0, now=float(seq)), 90)

    def test_explicit_battery_policy_retains_45_fps_option(self):
        policy = TargetPolicy()
        goals = [policy.update(90, 26.76, 80.28, "battery", True,
            sample_seq=seq, first_sample_seq=seq-9, span_s=3.0, now=float(seq)) for seq in (10, 20, 30)]
        self.assertEqual(goals, [90, 90, 45])

if __name__ == "__main__":
    unittest.main()
