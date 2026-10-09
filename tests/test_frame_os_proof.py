"""Frame OS A/B proof: control windows, paired measurements and the runner wiring."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "py_modules"))

from gfg_plugin.frame_os import proof  # noqa: E402
from gfg_plugin.frame_os.input_sensor import ABS_RX, EV_ABS, EVENT, InputState  # noqa: E402


def drive(meter, seconds, *, level, value_on, value_off, metric="freshness_ms", start=0.0, draw=False,
          level_at=None):
    """Run the meter at 10 Hz; the game answers each tick with the value for the control in effect."""
    control = None
    t = start
    seen = []
    while t < start + seconds:
        lvl = level_at(t) if level_at else level
        value = value_off if control else value_on
        telemetry = {} if draw else ({metric: value} if metric == "freshness_ms" else {metric: 1000.0 / value})
        meter.observe(t, eligible=True, level=lvl, telemetry=telemetry, draw_w=value if draw else None)
        control = meter.control(t, lvl)
        seen.append(control)
        t = round(t + 0.1, 3)
    return seen


class ProofMeterTests(unittest.TestCase):
    def test_calm_measures_response_from_shaping_off_windows(self):
        m = proof.ProofMeter()
        seen = drive(m, 200, level="calm", value_on=13.0, value_off=25.0)
        self.assertIn("no-shaping", seen)
        self.assertLess(seen.count("no-shaping") / len(seen), 0.25, "control windows stay rare")
        r = m.summary()["response"]
        self.assertTrue(r["measured"])
        self.assertAlmostEqual(r["mean"], 48.0, delta=1.0)        # (25 - 13) / 25
        self.assertEqual(m.summary()["frames"]["n"], 0)

    def test_boost_measures_frames_and_rest_measures_energy(self):
        m = proof.ProofMeter()
        seen = drive(m, 200, level="boost", value_on=45.0, value_off=30.0,
                     metric="present_interval_p50_ms")
        self.assertIn("hold-calm", seen)
        self.assertAlmostEqual(m.summary()["frames"]["mean"], 50.0, delta=1.0)
        m = proof.ProofMeter()
        drive(m, 200, level="rest", value_on=6.0, value_off=10.0, draw=True)
        self.assertAlmostEqual(m.summary()["energy"]["mean"], 40.0, delta=1.0)

    def test_a_changed_moment_is_not_a_pair(self):
        m = proof.ProofMeter()
        # the level flips every 3 s: no window can finish in one moment
        drive(m, 120, level=None, value_on=13.0, value_off=25.0,
              level_at=lambda t: "calm" if int(t // 3) % 2 == 0 else "boost")
        s = m.summary()
        self.assertEqual((s["response"]["n"], s["frames"]["n"]), (0, 0))
        self.assertGreater(s["aborted"], 0)

    def test_disabled_or_ineligible_never_controls(self):
        m = proof.ProofMeter()
        m.enabled = False
        self.assertEqual(set(drive(m, 120, level="calm", value_on=13.0, value_off=25.0)), {None})
        m = proof.ProofMeter()
        for i in range(1200):
            m.observe(i / 10, eligible=False, level="calm", telemetry={"freshness_ms": 13.0}, draw_w=None)
            self.assertIsNone(m.control(i / 10, "calm"))

    def test_missing_measurements_abort_instead_of_inventing(self):
        m = proof.ProofMeter()
        drive(m, 120, level="rest", value_on=None, value_off=None, draw=True)     # no draw sensor
        self.assertEqual(m.summary()["energy"]["n"], 0)

    def test_tests_get_rarer_once_everything_is_measured(self):
        m = proof.ProofMeter()
        m.pairs = {k: [10.0] * proof.SETTLED_PAIRS for k in proof.METRICS}
        m.test = proof.TESTS["calm"]
        m._finish(100.0)
        self.assertEqual(m.next_at, 100.0 + proof.SETTLED_GAP_S)
        m.pairs["response"] = []
        m.test = proof.TESTS["calm"]
        m._finish(200.0)
        self.assertEqual(m.next_at, 200.0 + proof.GAP_S)

    def test_stats(self):
        self.assertEqual(proof.stats([])["measured"], False)
        s = proof.stats([40.0, 50.0, 60.0])
        self.assertEqual((s["n"], s["mean"], s["measured"]), (3, 50.0, True))
        self.assertAlmostEqual(s["low"], 50.0 - 4.30 * 10.0 / 3 ** 0.5, delta=0.1)
        self.assertLess(s["low"], s["mean"])


class FakeChannel:
    """The pacer as Act sees it: frame age depends on tick shaping, real cadence on the published rate."""

    def __init__(self):
        self.policy = None
        self.writes = []

    def reset(self):
        return True

    def write_policy(self, **kw):
        self.policy = kw
        self.writes.append(kw)
        return True

    def heartbeat(self):
        return True

    def read_telemetry(self):
        if not self.policy or not self.policy.get("enabled"):
            return {"live": False}
        hz = self.policy["real_hz"]
        return {"live": True, "freshness_ms": 13.0 if self.policy["tick_shaping"] else 25.0,
                "present_interval_p50_ms": 1000.0 / hz, "applied_generation": self.policy["generation"]}

    def close(self):
        pass


class FakeReader:
    def __init__(self):
        self.state = InputState()
        self.available = False

    def poll(self):
        return 0

    def close(self):
        pass

    def status(self):
        return {}


class RunnerProofTests(unittest.TestCase):
    def make(self):
        from gfg_plugin.frame_os.runner import FrameOsRunner
        channel, reader = FakeChannel(), FakeReader()
        r = FrameOsRunner(channel, clock=lambda: 0.0, reader_factory=lambda: reader)
        r.configure(enabled=True, mode="act", output_hz=90, calm_real_hz=30, max_multiplier=3.0, calm_w=10.0)
        r.executor_active = True
        return r, channel, reader

    def test_calm_play_turns_the_response_ring_into_a_measurement(self):
        r, channel, _reader = self.make()
        shaping_off = 0
        for i in range(2000):
            status = r.tick(i / 10)
            shaping_off += status["ab_control"] == "no-shaping"
        self.assertGreater(shaping_off, 0)
        self.assertTrue(any(not w["tick_shaping"] for w in channel.writes), "control windows reach the pacer")
        self.assertTrue(channel.writes[-1]["tick_shaping"] or status["ab_control"])
        b = status["benefit"]
        self.assertTrue(b["measured"]["response"])
        self.assertAlmostEqual(b["response_pct"], 48.0, delta=1.0)
        self.assertEqual(status["proof"]["response"]["n"] >= proof.MIN_PAIRS, True)

    def test_a_held_boost_publishes_calm_without_watts_or_backoff(self):
        r, channel, reader = self.make()
        r.policy.broker.bank_j = 1e9
        r.policy.broker.max_bank_s = 1e9
        held = 0
        t = 0.0
        for i in range(2000):
            t = i / 10
            reader.state.feed(EVENT.pack(int(t), int((t % 1) * 1e6), EV_ABS, ABS_RX, 32000 if i % 2 else 31000))
            status = r.tick(t)
            if status["ab_control"] == "hold-calm":
                held += 1
                self.assertEqual(channel.policy["real_hz"], 30.0)
                self.assertEqual(r.tdp_offset_w, 0.0)
                self.assertEqual(status["decision"]["reason"], "ab-control")
        self.assertGreater(held, 0)
        self.assertFalse(any("boost-ineffective" in h for h in r.policy.history))
        self.assertAlmostEqual(status["benefit"]["frames_pct"], 50.0, delta=1.0)
        self.assertTrue(status["benefit"]["measured"]["frames"])

    def test_no_boost_back_off_before_the_executor_is_in_place(self):
        # review 1.3.0: without the executor the pacer runs calm, so every boost looked ineffective
        r, channel, reader = self.make()
        r.executor_active = False
        r.policy.broker.bank_j = 1e9
        r.policy.broker.max_bank_s = 1e9
        for i in range(100):
            t = i / 10
            reader.state.feed(EVENT.pack(int(t), int((t % 1) * 1e6), EV_ABS, ABS_RX, 32000 if i % 2 else 31000))
            r.tick(t)
        self.assertFalse(any("boost-ineffective" in h for h in r.policy.history))

    def test_a_hold_calm_window_clears_a_pending_boost_proof(self):
        r, _channel, reader = self.make()
        r.policy.broker.bank_j = 1e9
        r.policy.broker.max_bank_s = 1e9
        held = 0
        for i in range(2000):
            t = i / 10
            reader.state.feed(EVENT.pack(int(t), int((t % 1) * 1e6), EV_ABS, ABS_RX, 32000 if i % 2 else 31000))
            r.policy._boost_since = t - 2.0       # a proof pending from just before the window
            status = r.tick(t)
            if status["ab_control"] == "hold-calm":
                held += 1
                self.assertIsNone(r.policy._boost_since)
        self.assertGreater(held, 0)

    def test_off_switch_keeps_model_estimates(self):
        r, channel, _reader = self.make()
        r.proof.enabled = False
        for i in range(1200):
            status = r.tick(i / 10)
        self.assertTrue(all(w["tick_shaping"] for w in channel.writes))
        self.assertEqual(status["benefit"]["measured"], {"response": False, "frames": False, "energy": False})

    def test_observe_never_runs_control_windows(self):
        r, channel, _reader = self.make()
        r.configure(enabled=True, mode="observe", output_hz=90, calm_real_hz=30, max_multiplier=3.0, calm_w=10.0)
        for i in range(1200):
            self.assertIsNone(r.tick(i / 10)["ab_control"])


if __name__ == "__main__":
    unittest.main()


class ProofProvenanceTests(unittest.TestCase):
    def test_current_and_prior_statistics_are_separate(self):
        meter = proof.ProofMeter()
        meter.load({"response": [40.0, 42.0, 44.0]})
        result = meter.summary()["response"]
        self.assertEqual((result["n"], result["session_n"]), (3, 0))
        self.assertEqual(result["historical"]["mean"], 42.0)
        self.assertIsNone(result["session"]["mean"])
        meter.pairs["response"].append(12.0)
        result = meter.summary()["response"]
        self.assertEqual((result["n"], result["session_n"]), (4, 1))
        self.assertEqual(result["session"]["mean"], 12.0)
        self.assertFalse(result["session"]["measured"])
        self.assertEqual(result["historical"]["mean"], 42.0)

class LiveRingProvenanceTests(unittest.TestCase):
    def test_previous_backend_pairs_do_not_label_new_session_as_measured(self):
        from gfg_plugin.frame_os.runner import apply_proof
        meter = proof.ProofMeter()
        meter.load({"response": [40, 42, 44, 42, 43]})
        benefit = {"ready": False, "response_pct": None, "frames_pct": None, "energy_pct": None}
        result = apply_proof(benefit, meter.summary())
        self.assertFalse(result["ready"])
        self.assertFalse(result["measured"]["response"])
        self.assertIsNone(result["response_pct"])
        meter.pairs["response"].extend([10, 11, 12, 11, 10])
        result = apply_proof(benefit, meter.summary())
        self.assertTrue(result["measured"]["response"])
        self.assertAlmostEqual(result["response_pct"], 10.8)
        self.assertEqual(result["provenance"]["response"], "session-ab")
