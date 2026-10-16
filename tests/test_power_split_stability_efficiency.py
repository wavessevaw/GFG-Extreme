"""CPU/GPU Power Split: stable-point admission, safety and measurable A/B benefit.

All tests use a synthetic clock and mocked CPU sysfs. No Deck performance or
energy savings are inferred from these deterministic regressions.
"""
import asyncio
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "py_modules")]

from gfg_plugin import power_split as ps
from gfg_plugin.governor_core import BudgetController, WindowVerdict
from test_power_split import LADDER, run, sample
from test_governor_runtime import RuntimeBase


class SplitAdmissionAndSafety(unittest.TestCase):
    def test_no_step_during_unsettled_governor(self):
        s = ps.PowerSplit(LADDER)
        run(s, 130, fn=lambda t, split: ps.Sample(**{
            **vars(sample(top=15)), "steady": False}))
        self.assertEqual(s.level, 0)
        run(s, ps.STEP_GAP_S + 1, start=130, top=20)
        self.assertEqual(s.level, 1)

    def test_unsettled_governor_uncaps_during_probe_and_backs_off(self):
        s = ps.PowerSplit(LADDER)
        run(s, 22, top=20)
        self.assertEqual(s.level, 1)
        at = 22.0
        state = ps.Sample(**{**vars(sample(top=20)), "steady": False})
        self.assertIsNone(s.step(at, True, state))
        self.assertEqual(s.level, 0)
        self.assertEqual(s.reason, "governor-transition")
        run(s, ps.COOLDOWN_S - 1, start=23, top=20)
        self.assertEqual(s.level, 0)

    def test_telemetry_failure_uncaps_after_settle(self):
        s = ps.PowerSplit(LADDER)
        run(s, 26, top=20)
        self.assertEqual(s.level, 1)
        self.assertIsNone(s.step(26, True, sample(real=None, top=None)))
        self.assertEqual(s.level, 0)
        self.assertEqual(s.reason, "telemetry-unavailable")

    def test_not_only_boost_watts_but_verified_real_fps(self):
        s = ps.PowerSplit(LADDER)
        run(s, 28, top=20)
        self.assertEqual(s.level, 1)
        # An active real frame deficit is an immediate rollback even if the
        # GPU percentage and MHz still look impressive.
        self.assertIsNone(s.step(29, True, sample(real=24, top=20, gpu=99, mhz=1600)))
        self.assertEqual(s.reason, "real-frames-short")

    def test_memory_never_jumps_past_intermediate_rung(self):
        s = ps.PowerSplit(LADDER)
        s.start_level = 4
        run(s, ps.STEP_GAP_S + 1, top=15)
        self.assertEqual(s.level, 1)

    def test_malformed_boolean_telemetry_is_not_accepted(self):
        s = ps.PowerSplit(LADDER)
        run(s, 200, fn=lambda t, split: sample(real=True, top=False, gpu=True))
        self.assertEqual(s.level, 0)


class ABProofQuality(unittest.TestCase):
    def after_phase(self, before_real=30, after_real=30, control_real=30,
                    before_eff=140, after_eff=140, control_eff=120):
        s = ps.PowerSplit(LADDER)
        s.level = 1
        s.phase = "hold"
        s.ab_phase = "after"
        window = ps._Window(100)
        window.add(8, mhz=after_eff * 10, draw=10, real=after_real)
        s._ab = {"window": window, "tdp": 10, "level": 1, "target_real": 30,
                 "means": {"before": {"eff": before_eff, "draw": 10,
                                      "mhz": before_eff*10, "real": before_real},
                           "control": {"eff": control_eff, "draw": 10,
                                       "mhz": control_eff*10, "real": control_real}}}
        return s

    def complete(self, s):
        s._ab_step(111.0, 1.0, sample(real=30, top=20, tdp=10, draw=10))

    def test_capped_real_fps_regression_rejects_gpu_mhz_win(self):
        s = self.after_phase(before_real=29.5, after_real=29.5, control_real=30.5)
        self.complete(s)
        self.assertEqual(s.pairs, [])
        self.assertIsNone(s.ab_phase)

    def test_scene_drift_rejects_aba_even_if_average_looks_positive(self):
        s = self.after_phase(before_eff=140, after_eff=118, control_eff=115)
        self.complete(s)
        self.assertEqual(s.pairs, [])

    def test_missing_real_fps_rejects_aba(self):
        s = self.after_phase()
        s._ab["window"] = ps._Window(100)
        s._ab["window"].add(8, mhz=1400, draw=10)
        self.complete(s)
        self.assertEqual(s.pairs, [])

    def test_good_aba_is_recorded_with_real_frame_integrity(self):
        s = self.after_phase()
        self.complete(s)
        self.assertEqual(len(s.pairs), 1)
        self.assertGreater(s.pairs[0]["gain"], 10)
        self.assertEqual(s.pairs[0]["real"], 0)

    def test_four_independent_ineffective_pairs_stop_prolonged_cpu_cap(self):
        s = self.after_phase(before_eff=120, after_eff=120, control_eff=120)
        s.pairs = [{"gain": 0.1, "khz": LADDER[1]} for _ in range(3)]
        self.complete(s)
        self.assertEqual(s.level, 0)
        self.assertEqual(s.reason, "split-no-measured-benefit")
        self.assertGreater(s.failed.get(1, 0), 111)
        self.assertIsNone(s.cap_khz)

    def test_inconsistent_target_aborts_a_b_a(self):
        s = self.after_phase()
        s._ab_step(111, 1, sample(target=45, tdp=10))
        self.assertEqual(s.pairs, [])
        self.assertIsNone(s.ab_phase)


class SplitMemoryQuality(unittest.TestCase):
    def test_unmeasured_held_level_is_not_reused_next_session(self):
        m = ps.SplitMemory()
        m.start_session()
        s = ps.PowerSplit(LADDER)
        s.best_level = 3
        self.assertFalse(m.record(s))
        self.assertEqual(m.level, 0)

    def test_proven_same_level_positive_pairs_are_remembered(self):
        m = ps.SplitMemory()
        m.start_session()
        s = ps.PowerSplit(LADDER)
        s.best_level = 2
        s.pairs = [{"gain": 7.5, "khz": LADDER[2]} for _ in range(4)]
        self.assertTrue(m.record(s))
        self.assertEqual(m.level, 2)
        self.assertEqual(len(m.pairs), 4)

    def test_different_level_efficiency_does_not_validate_best_level(self):
        m = ps.SplitMemory()
        m.start_session()
        s = ps.PowerSplit(LADDER)
        s.best_level = 3
        s.pairs = [{"gain": 8.0, "khz": LADDER[1]} for _ in range(4)]
        m.record(s)
        self.assertEqual(m.level, 0)


class InterleavedGovernorResourceArbitration(unittest.TestCase):
    def test_cpu_probe_prevents_optional_tdp_reprobe_but_not_forever(self):
        c = BudgetController(target_output_fps=90, now=0,
                             min_tdp_w=6, max_tdp_w=15)
        c.phase = "locked"
        c.locked_since = 0
        c.settled_since = 10
        c.good = c.HEALTHY_WINDOWS
        c.reprobe_interval = c.REPROBE_S
        c.hold_cpu_split = True
        before = (c.idx, c.tdp, c.phase)
        self.assertEqual(c.observe(1000, WindowVerdict(True, False, "holds"),
                                   c.point.base_target_fps, 90), "hold")
        self.assertEqual((c.idx, c.tdp, c.phase), before)
        c.hold_cpu_split = False
        self.assertEqual(c.observe(1020, WindowVerdict(True, False, "holds"),
                                   c.point.base_target_fps, 90), "move")
        self.assertNotEqual((c.idx, c.tdp, c.phase), before)

    def test_active_cpu_split_does_not_disable_emergency_guard(self):
        c = BudgetController(target_output_fps=90, now=0,
                             min_tdp_w=6, max_tdp_w=15)
        c.phase = "locked"
        c.hold_cpu_split = True
        verdict = WindowVerdict(False, True, "real-below-cap", short=True)
        c.observe(100, verdict, 20, 60)
        self.assertNotEqual(c.last_reason, "cpu-split-hold",
                            "a CPU proof window must not mask unhealthy frames")


class GovernorPowerSplitActuation(RuntimeBase):
    def test_planned_gpu_vrs_trial_restores_prior_split_cap(self):
        self.assertTrue(self.svc.cpu.claim())
        self.assertTrue(self.svc.cpu.set_cap_khz(LADDER[1]))
        self.svc._split = ps.PowerSplit(LADDER)
        self.svc._split.level = 1
        self.svc._split.phase = "hold"
        self.svc._split._last = self.t["now"] - 1
        self.svc._autopilot_blocks_planned = lambda: True
        asyncio.run(self.svc._sync_power_split("game"))
        self.assertEqual(self.svc._split.level, 0)
        self.assertFalse(self.svc.cpu.owned)
        self.assertEqual(self.svc._status["power_split"]["phase"], "frozen")
        for policy in self.cpufreq.glob("policy*/scaling_max_freq"):
            self.assertEqual(int(policy.read_text()), 3_500_000)

    def test_pure_observation_does_not_claim_cpu_sysfs(self):
        split = ps.PowerSplit(LADDER)
        self.svc._split = split
        self.svc._split_key = ("game", ())
        self.svc._launch = {"running": False}
        self.svc._autopilot_blocks_planned = lambda: False
        self.svc._split_ready = ("30x3", 30.0)
        self.svc._budget = SimpleNamespace(
            point=SimpleNamespace(key="30x3"), tdp_control=True,
            phase="locked", probe=None)
        self.svc.power.claim()
        self.svc._applied_tdp = 10.0
        self.svc.sensors.sample = lambda: {"gpu_busy_pct": 97.0,
                                           "cpu_top_core_pct": 20.0, "gpu_clock_mhz": 1200}
        self.svc._status["sensors"] = self.svc.sensors.sample()
        with patch.object(self.svc.cpu, "claim", wraps=self.svc.cpu.claim) as claim:
            asyncio.run(self.svc._sync_power_split("game"))
        self.assertEqual(claim.call_count, 0)
        self.assertFalse(self.svc.cpu.owned)
        self.assertEqual(split.level, 0)


if __name__ == "__main__":
    unittest.main()
