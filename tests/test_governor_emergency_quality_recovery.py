"""Field regression: 2.1.4 Deck trace, 23x3.913 for 8+ minutes despite quality debt.

The intermediate 24x3.75/26x3.5/28x3.25 points were rejected by the
renderer. Emergency recovery must not be blocked by their rejection TTL.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "py_modules")]

from gfg_plugin.governor_core import BudgetController, WindowVerdict

GOOD = WindowVerdict(True, False, "holds")
BAD = WindowVerdict(False, True, "real-below-cap", short=True)


def emergency(*, tdp=15.0, now=150.0):
    c = BudgetController(target_output_fps=90, now=0.0, min_tdp_w=6, max_tdp_w=15)
    assert c.points[c.comfort_idx].key == "30x3"
    assert c.points[0].key == "23x3.913"
    c.idx = 0
    c.phase = "locked"
    c.tdp = tdp
    c.last_good = (0, tdp)
    c.settled_since = 1.0
    c.locked_since = 1.0
    c._now = now
    return c


class EmergencyQualityRecoveryTests(unittest.TestCase):
    def test_rejected_intermediate_ratios_do_not_block_normal_recovery(self):
        c = emergency()
        for key in ("24x3.75", "26x3.5", "28x3.25"):
            c.rejected[key] = 120.0
        self.assertEqual(c._reprobe(150.0), "move")
        self.assertEqual(c.point.key, "30x3")
        self.assertEqual(c.probe, "up")
        self.assertEqual(c.last_reason, "reprobe-emergency-quality-recovery")
        self.assertEqual(c.tdp, 15.0)

    def test_failed_quality_trial_rolls_back_and_blocks_repeat(self):
        c = emergency()
        c._reprobe(150.0)
        self.assertEqual(c._unhealthy(160.0, BAD, 22.5, 90.0), "move")
        self.assertEqual(c.point.key, "23x3.913")
        self.assertEqual(c.phase, "locked")
        self.assertIsNone(c.probe)
        self.assertEqual(c.tdp, 15.0)
        self.assertIn("30x3", c.rejected)
        self.assertEqual(c._reprobe(170.0), "move")
        self.assertEqual(c.point.key, "23x3.913")
        self.assertEqual(c.probe, "down", "rejected quality probe must back off, not thrash")

    def test_previously_rejected_comfort_cadence_stays_blocked(self):
        c = emergency()
        c.rejected["30x3"] = 145.0
        self.assertEqual(c._reprobe(150.0), "move")
        self.assertEqual(c.point.key, "23x3.913")
        self.assertEqual(c.tdp, 14.0)
        self.assertEqual(c.probe, "down")

    def test_recover_proven_headroom_before_changing_renderer_point(self):
        c = emergency(tdp=10.0)
        c.held = [(120.0, 13.0)]
        c._held_context = {(120.0, 13.0): "30x3"}
        self.assertEqual(c._reprobe(150.0), "move")
        self.assertEqual(c.point.key, "23x3.913")
        self.assertEqual(c.tdp, 13.0)
        self.assertIsNone(c.probe)
        self.assertTrue(c._validation_pending)
        self.assertIsNone(c.settled_since)
        # The restored power is not automatically a proven quality result.
        c.observe(155.0, GOOD, 22.5, 90.0)
        self.assertEqual(c.point.key, "23x3.913")
        self.assertEqual(c.last_good, (0, 10.0))
        c.observe(165.0, GOOD, 22.5, 90.0)
        self.assertEqual(c.last_good, (0, 13.0))

    def test_hot_device_does_not_try_harder_quality_point(self):
        c = emergency()
        c.set_thermal("hot", 150.0)
        self.assertEqual(c._reprobe(150.0), "move")
        self.assertEqual(c.point.key, "23x3.913")
        self.assertEqual(c.tdp, 14.0)

    def test_normal_cadence_retains_watts_first_policy(self):
        c = BudgetController(target_output_fps=90, now=0.0, min_tdp_w=6, max_tdp_w=15)
        c.phase = "locked"
        c.tdp = 13.0
        c.last_good = (c.idx, 13.0)
        self.assertEqual(c.point.key, "30x3")
        self.assertEqual(c._reprobe(150.0), "move")
        self.assertEqual(c.point.key, "30x3")
        self.assertEqual(c.tdp, 12.0)


if __name__ == "__main__":
    unittest.main()
