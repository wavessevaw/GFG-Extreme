import sys, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "py_modules"))
from gfg_plugin.governor_core import EffortEstimator, raw_effort  # noqa: E402


def pt(m=2, scale=100):
    return {"multiplier": m, "render_scale_pct": scale}


class RawEffortTests(unittest.TestCase):
    def test_levels(self):
        self.assertEqual(raw_effort(pt(1), 60), "easy")
        self.assertEqual(raw_effort(pt(2), 45), "medium")
        self.assertEqual(raw_effort(pt(3), 30), "hard")
        self.assertEqual(raw_effort(pt(2, 90), 45), "hard")
        self.assertEqual(raw_effort(pt(3, 80), 30), "nightmare")

    def test_very_low_base_fps_is_nightmare(self):
        self.assertEqual(raw_effort(pt(3), 15), "nightmare")
        self.assertEqual(raw_effort(pt(3), 20), "hard")  # x3 for 60 FPS is not hopeless

    def test_exhausted_and_no_point(self):
        self.assertEqual(raw_effort(None, None, exhausted=True), "nightmare")
        self.assertIsNone(raw_effort(None, 40))


class EstimatorTests(unittest.TestCase):
    def run_for(self, est, raw, start, seconds, step=1.0):
        t = start
        while t < start + seconds:
            est.update(t, raw)
            t += step
        return t

    def test_nothing_published_immediately(self):
        e = EffortEstimator()
        self.assertIsNone(e.update(0, "hard"))
        self.assertIsNone(e.update(EffortEstimator.INITIAL_DWELL - 1, "hard"))
        self.assertEqual(e.update(EffortEstimator.INITIAL_DWELL, "hard"), "hard")

    def test_flapping_input_never_publishes(self):
        e = EffortEstimator()
        for i in range(200):
            e.update(float(i * 5), "medium" if i % 2 else "hard")
        self.assertIsNone(e.level)

    def test_up_fast_down_slow_single_step(self):
        e = EffortEstimator()
        t = self.run_for(e, "medium", 0, 50)
        self.assertEqual(e.level, "medium")
        t = self.run_for(e, "hard", t, EffortEstimator.MIN_HOLD + 6)
        self.assertEqual(e.level, "hard")
        t = self.run_for(e, "easy", t, EffortEstimator.DOWN_DWELL - 5)
        self.assertEqual(e.level, "hard")  # not yet
        t = self.run_for(e, "easy", t, 10)
        self.assertEqual(e.level, "medium")  # one step only
        t = self.run_for(e, "easy", t, EffortEstimator.DOWN_DWELL + 1)
        self.assertEqual(e.level, "easy")

    def test_nightmare_is_reported_directly(self):
        e = EffortEstimator()
        t = self.run_for(e, "easy", 0, 50)
        self.run_for(e, "nightmare", t, EffortEstimator.MIN_HOLD + 6)
        self.assertEqual(e.level, "nightmare")

    def test_brief_blip_does_not_change_level(self):
        e = EffortEstimator()
        t = self.run_for(e, "medium", 0, 50)
        t = self.run_for(e, "hard", t, 10)
        t = self.run_for(e, "medium", t, 30)
        self.assertEqual(e.level, "medium")

    def test_pause_keeps_level_and_reset_clears(self):
        e = EffortEstimator()
        t = self.run_for(e, "medium", 0, 50)
        e.update(t, None)
        self.assertEqual(e.level, "medium")
        e.reset()
        self.assertEqual(e.status(), {"level": None, "assessing": True})


if __name__ == "__main__":
    unittest.main()
