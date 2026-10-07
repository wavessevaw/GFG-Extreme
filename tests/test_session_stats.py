import sys, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "py_modules"))
from gfg_plugin.session_stats import SessionStats  # noqa: E402


class SessionStatsTests(unittest.TestCase):
    def test_time_weighted_averages_and_savings(self):
        s = SessionStats()
        s.start((1, 2, 3), 0.0)
        t = 0.0
        for _ in range(60):                  # 60 s at 9 W
            t += 1.0
            s.add(t, output=90, real=30, tdp=9, draw=8.5, reference_w=20)
        for _ in range(30):                  # 30 s at 12 W
            t += 1.0
            s.add(t, output=90, real=30, tdp=12, draw=11.5, reference_w=20)
        r = s.summary()
        self.assertEqual(r["minutes"], 1.5)
        self.assertEqual(r["avg_output_fps"], 90.0)
        self.assertEqual(r["avg_tdp_w"], 10.0)
        self.assertEqual(r["saved_w"], 10.0)
        self.assertEqual(s.finish()["avg_draw_w"], 9.5)
        self.assertIsNone(s.summary())

    def test_short_sessions_and_long_gaps(self):
        s = SessionStats()
        s.start("k", 0.0)
        s.add(10.0, output=90, real=30, tdp=9, draw=None, reference_w=None)   # gap capped at 5 s
        self.assertIsNone(s.summary(), "under 30 s is not a session")
        for i in range(30):
            s.add(11.0 + i, output=60, real=30, tdp=None, draw=None, reference_w=None)
        r = s.summary()
        self.assertEqual(r["minutes"], round(35 / 60, 1))
        self.assertIsNone(r["saved_w"])


if __name__ == "__main__":
    unittest.main()
