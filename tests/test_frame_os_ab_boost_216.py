"""2.1.6 field-inspired provenance and hardware TDP accounting regressions.

Simulated measurements here prove the control loop cannot *claim* an effect
without pacer acknowledgement; they do not prove a real Deck FPS/power gain.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "py_modules"))

from gfg_plugin.frame_os.runner import FrameOsRunner
from gfg_plugin.frame_os.input_sensor import InputState, ABS_RX, EV_ABS, EVENT
from test_frame_os_proof import FakeChannel, FakeReader


class NoAckChannel(FakeChannel):
    def read_telemetry(self):
        t = super().read_telemetry()
        if t.get("live"):
            t["applied_generation"] = max(0, t["applied_generation"] - 1)
        return t


class StalePresentChannel(FakeChannel):
    def read_telemetry(self):
        t = super().read_telemetry()
        if t.get("live"):
            t["last_present_ns"] = 1000  # same real-present publication every 100ms
        return t


class RejectControlChannel(FakeChannel):
    def write_policy(self, **kw):
        if self.policy and not kw.get("tick_shaping", True):
            return False  # no-shaping A/B control was never applied
        return super().write_policy(**kw)


def runner(channel=None, *, applied_tdp_w=None):
    channel = channel or FakeChannel()
    reader = FakeReader()
    r = FrameOsRunner(channel, clock=lambda: 0.0, reader_factory=lambda: reader)
    r.configure(enabled=True, mode="act", output_hz=90, calm_real_hz=30,
                max_multiplier=3.0, calm_w=10.0)
    r.executor_active = True
    r.applied_tdp_w = applied_tdp_w
    return r, channel, reader


class CausalProofTests(unittest.TestCase):
    def test_unacknowledged_generation_cannot_record_even_one_positive_pair(self):
        r, c, _ = runner(NoAckChannel())
        for i in range(1500):
            status = r.tick(i / 10)
        self.assertFalse(status["proof_policy_acknowledged"])
        self.assertEqual(status["proof"]["response"]["session_n"], 0)
        self.assertEqual(status["benefit"]["provenance"]["response"], "model-or-telemetry")
        self.assertFalse(status["benefit"]["measured"]["response"])

    def test_repeated_real_present_counter_cannot_prove_shaping_gain(self):
        r, c, _ = runner(StalePresentChannel())
        for i in range(1500):
            status = r.tick(i / 10)
        self.assertEqual(status["proof"]["response"]["session_n"], 0)
        self.assertFalse(status["proof_policy_acknowledged"])

    def test_failed_pacer_control_write_cannot_generate_positive_aba(self):
        r, c, _ = runner(RejectControlChannel())
        for i in range(1600):
            status = r.tick(i / 10)
        self.assertEqual(status["proof"]["response"]["session_n"], 0)
        self.assertGreater(status["proof"]["aborted"], 0)

    def test_acknowledged_consecutive_presents_still_measure_shaping(self):
        class FreshChannel(FakeChannel):
            count = 0
            def read_telemetry(self):
                v = super().read_telemetry()
                if v.get("live"):
                    self.count += 1
                    v["last_present_ns"] = self.count * 100_000_000
                return v
        r, c, _ = runner(FreshChannel())
        for i in range(1500):
            status = r.tick(i / 10)
        self.assertGreaterEqual(status["proof"]["response"]["session_n"], 3)
        self.assertTrue(status["proof"]["response"]["session"]["measured"])
        self.assertAlmostEqual(status["benefit"]["response_pct"], 48.0, delta=2)


class RealAppliedPowerTests(unittest.TestCase):
    def test_requested_boost_watts_do_not_create_fake_energy_savings(self):
        r, c, reader = runner(applied_tdp_w=None)
        r.policy.broker.bank_j = 100
        reader.state.feed(EVENT.pack(0, 0, EV_ABS, ABS_RX, 32000))
        seen = []
        for i in range(150):
            status = r.tick(i / 10)
            seen.append(status["decision"]["level"])
        self.assertIn("boost", seen)
        self.assertIsNone(status["benefit"]["energy_pct"])
        self.assertFalse(status["boost_tdp_offset_applied"])
        self.assertIsNone(status["hardware_tdp_w"])

    def test_fixed_governor_tdp_yields_no_pretend_boost_or_rest_saving(self):
        r, c, reader = runner(applied_tdp_w=10.0)
        r.policy.broker.bank_j = 100
        reader.state.feed(EVENT.pack(0, 0, EV_ABS, ABS_RX, 32000))
        for i in range(120):
            status = r.tick(i / 10)
        self.assertEqual(status["hardware_tdp_w"], 10.0)
        self.assertEqual(status["benefit"]["energy_pct"], 0.0)

    def test_unsettled_governor_cap_does_not_bill_its_transition_to_act(self):
        r, c, _ = runner(applied_tdp_w=8.0)
        # While Governor is lowering its power, old hardware cap != new calm.
        for i in range(120):
            status = r.tick(i / 10)
        self.assertIsNone(status["benefit"]["energy_pct"])


if __name__ == "__main__":
    unittest.main()
