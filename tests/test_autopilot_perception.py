import sys
import unittest
from dataclasses import FrozenInstanceError, replace
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "py_modules"))
from gfg_plugin.autopilot.contracts import Bottleneck as B, Config, Host, Sample, Snapshot
from gfg_plugin.autopilot.perception import perceive


def snapshot(output=90, real=45, gpu=50, cpu=50):
    return Snapshot("game:pid:start:epoch", 108,
                    tuple(Sample(i + 1, 100 + i * 2, "renderer", real, output) for i in range(5)),
                    Host(108, 5, gpu, cpu, 70), target_fps=90, context="renderer")


class PerceptionTests(unittest.TestCase):
    def test_stable_high_gpu_is_not_a_bottleneck(self):
        self.assertEqual(perceive(snapshot(gpu=99), 108).primary, B.STABLE)

    def test_correlated_gpu_and_cpu_deficits(self):
        for gpu, cpu, expected in ((99, 40, B.GPU_LIMITED), (40, 99, B.CPU_LIMITED),
                                   (99, 99, B.UNKNOWN), (40, 40, B.UNKNOWN)):
            with self.subTest(gpu=gpu, cpu=cpu):
                self.assertEqual(perceive(snapshot(60, gpu=gpu, cpu=cpu), 108).primary, expected)

    def test_missing_zero_and_nonfinite_are_distinct(self):
        zero = snapshot(0, gpu=40, cpu=40)
        self.assertEqual(perceive(zero, 108).primary, B.UNKNOWN)
        for value in (None, float("nan"), float("inf"), -1, True):
            result = perceive(snapshot(value), 108)
            self.assertEqual(result.reason, "measured-fps-unavailable")
        self.assertNotEqual(perceive(zero, 108).reason, "measured-fps-unavailable")

    def test_stale_missing_and_future_host(self):
        for host in (None, Host(100, 1, 99, 20), Host(110, 1, 99, 20)):
            self.assertEqual(perceive(replace(snapshot(60), host=host), 108).primary, B.UNKNOWN)

    def test_no_unverified_thermal_or_power_diagnosis(self):
        s = snapshot(60)
        self.assertEqual(perceive(replace(s, host=Host(108, 5, 50, 50, 99)), 108).primary, B.UNKNOWN)
        verified = replace(s, host=Host(108, 5, 50, 50, 90, 90, 12, 12))
        r = perceive(verified, 108)
        self.assertEqual(r.primary, B.THERMAL_LIMITED)
        self.assertIn(B.POWER_LIMITED, r.secondary)

    def test_fg_pressure_requires_distinct_fresh_events(self):
        s = replace(snapshot(60), pressure=((21, 107, "renderer"),) * 5)
        self.assertEqual(perceive(s, 108).primary, B.UNKNOWN)
        s = replace(s, pressure=tuple((21+i, 107, "renderer") for i in range(3)))
        self.assertEqual(perceive(s, 108).primary, B.FG_LIMITED)
        self.assertEqual(perceive(replace(s, pressure=((22, 100, "renderer"),)), 108).primary, B.UNKNOWN)

    def test_external_menu_and_restore_block(self):
        for reason in ("focus-unconfirmed-or-menu", "restore-pending", "runtime-not-observing"):
            self.assertEqual(perceive(replace(snapshot(), blocked_reason=reason), 108).reason, reason)
        self.assertEqual(perceive(replace(snapshot(), backend="optiscaler"), 108).primary, B.UNKNOWN)

    def test_sequence_context_clock_and_gap_guards(self):
        s = snapshot()
        invalid = (
            (s.samples[0],) * 5,
            tuple(replace(x, context="foreign") for x in s.samples),
            tuple(replace(x, timestamp_mono=108) for x in s.samples),
            tuple(replace(x, timestamp_mono=100 + i * 3) for i, x in enumerate(s.samples)),
        )
        for samples in invalid:
            self.assertEqual(perceive(replace(s, samples=samples), 108).primary, B.UNKNOWN)
        self.assertTrue(perceive(s, 112).stale)

    def test_deterministic_immutable_and_expiry(self):
        s = snapshot()
        self.assertEqual(perceive(s, 108), perceive(s, 108))
        self.assertEqual(perceive(s, 108).expires_at, 110.5)
        with self.assertRaises(FrozenInstanceError):
            s.session_key = "changed"
        with self.assertRaises(ValueError):
            Config(max_age_s=float("nan"))
        with self.assertRaises(ValueError):
            Config(min_samples=1)

    def test_short_or_single_observation_is_not_stable(self):
        s = snapshot()
        self.assertEqual(perceive(replace(s, samples=s.samples[-1:]), 108).reason, "baseline-incomplete")


if __name__ == "__main__":
    unittest.main()
