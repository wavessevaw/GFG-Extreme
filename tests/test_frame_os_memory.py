"""Frame OS memory: per-game verdicts from A/B pairs, re-checks, and predictive boost."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "py_modules"))
sys.path.insert(0, str(ROOT / "tests"))

from gfg_plugin.frame_os import memory  # noqa: E402
from gfg_plugin.frame_os.policy import InjectionPolicy  # noqa: E402


class VerdictTests(unittest.TestCase):
    def test_verdicts(self):
        self.assertEqual(memory.verdict("response", [40.0, 45.0]), "unclear")          # too few
        self.assertEqual(memory.verdict("response", [40.0, 45.0, 50.0]), "helps")
        self.assertEqual(memory.verdict("response", [-8.0, -10.0, -9.0]), "hurts")
        self.assertEqual(memory.verdict("response", [-20.0, 30.0, 5.0]), "unclear")
        self.assertEqual(memory.verdict("frames", [1.0, 0.5, 1.5, 0.0]), "useless")
        self.assertEqual(memory.verdict("frames", [48.0, 50.0, 52.0]), "helps")
        self.assertEqual(memory.verdict("energy", [1.0, 0.5, 1.5, 0.0]), "unclear", "only frames can be useless")


class GameMemoryTests(unittest.TestCase):
    def test_harmful_effect_is_switched_off_and_rechecked_later(self):
        m = memory.GameMemory()
        m.start_session()
        self.assertEqual(m.add_pairs({"response": [-8.0, -10.0, -9.0]}), {"shaping": "hurts"})
        self.assertTrue(m.disabled()["shaping"])
        self.assertEqual(m.add_pairs({"response": [-9.0]}), {}, "already off: reported once")
        record = m.to_record()
        again = memory.GameMemory(record)
        for _ in range(memory.RECHECK_SESSIONS - 1):
            self.assertTrue(again.start_session()["shaping"])
        self.assertFalse(again.start_session()["shaping"], "re-checked after a while")
        self.assertEqual(again.pairs["response"], [], "old evidence does not outvote the re-check")

    def test_record_survives_bad_json_and_keeps_recent_pairs(self):
        m = memory.GameMemory({"pairs": {"frames": list(range(100)) + ["x"]}, "sessions": "3", "off": {"bogus": 1}})
        self.assertEqual(len(m.pairs["frames"]), memory.KEEP_PAIRS)
        self.assertEqual((m.sessions, m.off), (3, {}))
        self.assertEqual(memory.GameMemory("garbage").sessions, 0)

    def test_seed_pairs_only_when_measured(self):
        m = memory.GameMemory({"pairs": {"response": [40.0, 41.0, 42.0], "frames": [10.0]}})
        self.assertEqual(memory.seed_pairs(m), {"response": [40.0, 41.0, 42.0]})


class RunnerMemoryTests(unittest.TestCase):
    def test_runner_applies_memory(self):
        from test_frame_os_proof import FakeChannel, FakeReader
        from gfg_plugin.frame_os.runner import FrameOsRunner
        channel, reader = FakeChannel(), FakeReader()
        r = FrameOsRunner(channel, clock=lambda: 0.0, reader_factory=lambda: reader)
        r.configure(enabled=True, mode="act", output_hz=90, calm_real_hz=30, max_multiplier=3.0, calm_w=10.0)
        r.executor_active = True
        r.apply_memory({"shaping": True, "boost": True}, {"frames": [1.0, 0.5, 1.5]})
        for i in range(600):
            status = r.tick(i / 10)
        self.assertTrue(all(not w["tick_shaping"] for w in channel.writes), "shaping off for this game")
        self.assertIsNone(status["proof"]["testing"] if status["proof"]["phase"] == "wait" else None)
        self.assertFalse(r.policy.boost_allowed)
        self.assertEqual(status["proof"]["response"]["n"], 0, "no shaping: nothing to test")
        self.assertTrue(status["benefit"]["measured"]["frames"], "earlier sessions' pairs count")
        # a new policy (the Governor moved the point) keeps the per-game switches
        r.configure(enabled=True, mode="act", output_hz=90, calm_real_hz=45, max_multiplier=2.0, calm_w=10.0)
        self.assertFalse(r.policy.boost_allowed)


class PredictiveBoostTests(unittest.TestCase):
    def test_a_fast_rising_stick_boosts_before_the_threshold(self):
        p = InjectionPolicy(output_hz=90, calm_real_hz=30)
        self.assertEqual(p.tick(0.0, {"camera": 0.0}).level, "calm")
        d = p.tick(0.1, {"camera": 0.3})                  # +3.0/s from rest, still under 0.5
        self.assertEqual((d.level, d.reason), ("boost", "camera-onset"))

    def test_a_slow_drift_does_not(self):
        p = InjectionPolicy(output_hz=90, calm_real_hz=30)
        for i in range(10):
            d = p.tick(i / 10, {"camera": 0.03 * i})       # 0.3 /s
        self.assertEqual(d.level, "calm")

    def test_boost_off_for_game(self):
        p = InjectionPolicy(output_hz=90, calm_real_hz=30, boost_allowed=False)
        d = p.tick(0.0, {"camera": 0.9})
        self.assertEqual((d.level, d.reason), ("calm", "boost-off-for-game"))
        p = InjectionPolicy(output_hz=90, calm_real_hz=30, rest_allowed=False)
        self.assertEqual(p.tick(0.0, {"camera": 0.0}, focused=False).level, "calm")


if __name__ == "__main__":
    unittest.main()
