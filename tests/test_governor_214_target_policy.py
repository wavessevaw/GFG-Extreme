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

    def test_frame_os_act_cannot_override_governor_tdp(self):
        import asyncio
        from types import SimpleNamespace
        from unittest.mock import AsyncMock, MagicMock, patch
        from gfg_plugin.governor_service import GovernorService
        service = GovernorService.__new__(GovernorService)
        service._budget = SimpleNamespace(tdp_control=True, tdp=11.0, normal_max_w=15.0, min_w=3.0, last_reason="locked")
        service.power = SimpleNamespace(state=SimpleNamespace(owned=True), set_tdp_w=MagicMock(return_value={"success": True}))
        service.frame_os = SimpleNamespace(tdp_offset_w=4.0)
        service._applied_tdp = None
        service._autopilot_arbiter = SimpleNamespace(freeze_tdp=False)
        service._status = {}
        service._event = MagicMock()
        service._mark_autopilot_transition = MagicMock()
        service._evaluation_after_seq = 0
        service._tdp_set_seq = 0
        service._draw_samples = []
        service.observer = SimpleNamespace(sample_seq=10)
        service._mode = lambda profile: "autopilot"
        service._profile_enabled = lambda profile: True
        self.assertTrue(asyncio.run(service._apply_budget_tdp("game")))
        service.power.set_tdp_w.assert_called_once_with(11.0)
        service.frame_os.tdp_offset_w = 0.0
        self.assertTrue(asyncio.run(service._apply_budget_tdp("game")))
        service.power.set_tdp_w.assert_called_once()

if __name__ == "__main__":
    unittest.main()
