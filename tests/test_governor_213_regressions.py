"""GFG Extreme 2.1.3 regressions: idle TDP recovery, loading transitions and HUD cadence."""
import asyncio
import logging
import time
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path[:0] = [str(ROOT), str(ROOT / "py_modules")]

from gfg_plugin.autopilot.planner import TargetPolicy
from gfg_plugin.governor_core import BudgetController, OperatingPoint, window_verdict
from gfg_plugin.governor_service import GovernorService


class LoadingTransitionTests(unittest.TestCase):
    def test_non_generating_collapse_is_a_stall_not_a_power_failure(self):
        point = OperatingPoint("30x3", 90, 30, 3, 100)
        summary = {
            "real": {"p5": 14.0, "median": 15.0},
            "output": {"median": 15.0},
            "hard_pressure": 0,
            "misses": 0,
        }
        verdict = window_verdict(summary, point)
        self.assertTrue(verdict.stall)
        self.assertFalse(verdict.healthy)

    def test_real_gameplay_generating_three_times_is_not_a_loading_stall(self):
        point = OperatingPoint("30x3", 90, 30, 3, 100)
        summary = {
            "real": {"p5": 14.0, "median": 15.0},
            "output": {"median": 45.0},
            "hard_pressure": 0,
            "misses": 0,
        }
        self.assertFalse(window_verdict(summary, point).stall)

    def test_loading_transition_does_not_lower_autopilot_goal(self):
        policy = TargetPolicy()
        for seq in (10, 20, 30):
            goal = policy.update(
                90, 15, 15, "auto", True,
                sample_seq=seq, first_sample_seq=seq - 9, span_s=3.0,
                now=float(seq), loading_transition=True,
            )
            self.assertEqual(goal, 90)
        self.assertEqual(policy.target, 90)


class KnownGoodTdpRecoveryTests(unittest.TestCase):
    def test_fast_recovery_returns_to_recent_proven_work_tdp(self):
        budget = BudgetController(
            target_output_fps=90, now=100.0, min_tdp_w=3.0, max_tdp_w=15.0,
        )
        budget.tdp = 6.0
        budget.draw_w = 6.2
        budget.held = [(99.0, 10.0)]
        self.assertEqual(budget.fast_check(101.0, 15.0, 6.2), "hold")
        self.assertEqual(budget.fast_check(102.0, 15.0, 6.2), "move")
        self.assertGreaterEqual(budget.tdp, 10.0)
        self.assertLessEqual(budget.tdp, budget.ideal_max_w)

    def test_work_tdp_remembers_highest_proven_point_not_latest_economy_step(self):
        budget = BudgetController(
            target_output_fps=90, now=100.0, min_tdp_w=3.0, max_tdp_w=15.0,
        )
        budget.held = [(99.0, 10.0), (100.0, 9.0), (101.0, 7.0)]
        self.assertEqual(budget._work_tdp(102.0), 10.0)

    def test_fast_recovery_restores_known_good_point_above_ideal_budget(self):
        budget = BudgetController(
            target_output_fps=90, now=100.0, min_tdp_w=3.0, max_tdp_w=15.0,
        )
        budget.tdp = 6.0
        budget.draw_w = 6.2
        budget.held = [(99.0, 13.0), (100.0, 8.0), (101.0, 7.0)]
        self.assertEqual(budget.fast_check(101.0, 15.0, 6.2), "hold")
        self.assertEqual(budget.fast_check(102.0, 15.0, 6.2), "move")
        self.assertEqual(budget.tdp, 13.0)

    def test_failed_economy_probe_restores_work_tdp_not_only_previous_one_watt_step(self):
        budget = BudgetController(
            target_output_fps=90, now=100.0, min_tdp_w=3.0, max_tdp_w=15.0,
        )
        budget.tdp = 6.0
        budget.draw_w = 6.2
        budget.held = [(99.0, 10.0), (100.0, 9.0), (101.0, 7.0)]
        budget.probe = "down"
        budget.last_good = (budget.idx, 7.0)
        budget.phase = "search_down"
        self.assertEqual(budget._fast_raise(102.0), "move")
        self.assertEqual(budget.tdp, 10.0)
        self.assertIn("known-good", budget.last_reason)

    def test_autopilot_keeps_90_goal_while_known_good_tdp_recovery_is_possible(self):
        svc = GovernorService.__new__(GovernorService)
        svc._mode = lambda _profile: "autopilot"
        svc._profile_enabled = lambda _profile: True
        svc._autopilot_arbiter = SimpleNamespace(freeze_tdp=False)
        svc._autopilot_targets = TargetPolicy()
        svc._autopilot_preference = lambda _profile: "auto"
        svc._menu_since = None
        svc._menu_covering = lambda: False
        svc._autopilot_transition_seq = 0
        svc._generation_seen = None
        svc._clock = lambda: 102.0
        svc._status = {}
        budget = BudgetController(
            target_output_fps=90, now=100.0, min_tdp_w=3.0, max_tdp_w=15.0,
        )
        budget.tdp = 6.0
        budget.draw_w = 6.2
        budget.held = [(99.0, 10.0)]
        svc._budget = budget
        summary = {
            "samples": 8,
            "real": {"median": 15.0},
            "output": {"median": 45.0},
            "first_sample_seq": 1,
            "last_sample_seq": 10,
            "sample_span_s": 4.0,
        }
        snapshot = {"sample_age_ms": 100, "session_generation": 1}
        self.assertEqual(svc._governor_target("game", 90, summary, snapshot=snapshot), 90)
        self.assertEqual(svc._status.get("autopilot_target_hold_reason"), "known-good-tdp-recovery")


class HudWakeCadenceTests(unittest.TestCase):
    def test_frequent_wakeups_do_not_starve_half_second_hud_beat(self):
        async def scenario():
            svc = GovernorService.__new__(GovernorService)
            svc.LOOP_SECONDS = 1.0
            svc.IDLE_LOOP_SECONDS = 5.0
            svc._stop = asyncio.Event()
            svc._wake = asyncio.Event()
            svc.log = logging.getLogger("hud-wakeup-cadence")
            svc._is_idle = lambda: False
            calls = {"iterations": 0}
            hud_times = []

            async def iteration():
                calls["iterations"] += 1
                if calls["iterations"] >= 14:
                    svc._stop.set()

            async def wait_governor(_timeout):
                await asyncio.sleep(0.1)
                return True

            async def hud():
                hud_times.append(time.monotonic())

            svc._iteration = iteration
            svc._wait_governor = wait_governor
            svc._refresh_hud_beat = hud
            await svc._loop()
            self.assertGreaterEqual(len(hud_times), 2)
            gaps = [b - a for a, b in zip(hud_times, hud_times[1:])]
            self.assertTrue(all(0.45 <= gap <= 0.75 for gap in gaps), gaps)

        asyncio.run(scenario())


if __name__ == "__main__":
    unittest.main()
