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

    def test_heat_and_stutter_shares(self):
        s = SessionStats()
        s.start("k", 0.0)
        for i in range(60):
            s.add(1.0 + i, output=90, real=30, tdp=9, draw=None, reference_w=None,
                  temp_c=70 + i / 4, stuttering=i < 6, hot=i >= 45)
        r = s.summary()
        self.assertEqual(r["max_temp_c"], 85.0)
        self.assertEqual(r["stutter_pct"], 10)
        self.assertEqual(r["hot_pct"], 25)


    def test_seconds_per_mode_and_mixed_sessions(self):
        # review 1.1.x: the mode at the exit alone filed an 18 min Battery + 13 min Balanced session as Balanced.
        s = SessionStats()
        s.start("k", 0.0)
        t = 0.0
        for mode, seconds in (("budget", 18 * 60), ("balanced", 13 * 60), ("quality", 10)):
            for _ in range(seconds):
                t += 1.0
                s.add(t, output=90, real=30, tdp=9, draw=None, reference_w=None, mode=mode)
        r = s.summary()
        self.assertEqual(r["mode"], "mixed")
        self.assertEqual(r["modes"], {"budget": 18.0, "balanced": 13.0}, "a 10 s misclick is not a mode")
        self.assertEqual(list(r["modes"]), ["budget", "balanced"], "longest first")
        single = SessionStats()
        single.start("k", 0.0)
        for i in range(60):
            single.add(1.0 + i, output=90, real=30, tdp=9, draw=None, reference_w=None, mode="budget")
        self.assertEqual((single.summary()["mode"], single.summary()["modes"]), ("budget", {"budget": 1.0}))
        unknown = SessionStats()
        unknown.start("k", 0.0)
        for i in range(60):
            unknown.add(1.0 + i, output=90, real=30, tdp=9, draw=None, reference_w=None)
        self.assertNotIn("mode", unknown.summary(), "the service falls back to the current mode")

    def test_energy_saved_and_battery_minutes(self):
        s = SessionStats()
        s.start("k", 0.0)
        for i in range(30 * 60):                   # 30 min drawing 9 W against a 15 W limit, 12 W from the battery
            s.add(1.0 + i, output=90, real=30, tdp=10, draw=9, reference_w=15, battery_w=12.0)
        r = s.summary()
        self.assertEqual(r["saved_w"], 5.0, "the cap below the limit")
        self.assertEqual(r["saved_wh"], 3.0, "measured draw, not the cap")
        self.assertEqual(r["battery_minutes_gained"], 15)
        plugged = SessionStats()
        plugged.start("k", 0.0)
        for i in range(60):
            plugged.add(1.0 + i, output=90, real=30, tdp=10, draw=9, reference_w=15)
        self.assertEqual(plugged.summary()["saved_wh"], 0.1)
        self.assertNotIn("battery_minutes_gained", plugged.summary(), "no discharge rate: omitted")
        no_sensor = SessionStats()
        no_sensor.start("k", 0.0)
        for i in range(60):
            no_sensor.add(1.0 + i, output=90, real=30, tdp=9, draw=None, reference_w=15, battery_w=12.0)
        self.assertEqual(no_sensor.summary()["saved_w"], 6.0)
        self.assertIsNone(no_sensor.summary()["saved_wh"], "no measured draw: energy left out")
        self.assertNotIn("battery_minutes_gained", no_sensor.summary())

    def test_no_saving_above_the_limit_is_never_negative(self):
        s = SessionStats()
        s.start("k", 0.0)
        for i in range(60):                        # caps above the user's limit (Balanced/emergency)
            s.add(1.0 + i, output=90, real=30, tdp=17, draw=16, reference_w=15, battery_w=12.0)
        r = s.summary()
        self.assertIsNone(r["saved_w"], "never a negative saving")
        self.assertIsNone(r["saved_wh"])
        self.assertNotIn("battery_minutes_gained", r)
        lower_cap = SessionStats()
        lower_cap.start("k", 0.0)
        for i in range(60):                        # the cap is lower but the APU drew above the limit
            lower_cap.add(1.0 + i, output=90, real=30, tdp=14, draw=15.5, reference_w=15, battery_w=12.0)
        self.assertEqual(lower_cap.summary()["saved_w"], 1.0)
        self.assertIsNone(lower_cap.summary()["saved_wh"])
        self.assertNotIn("battery_minutes_gained", lower_cap.summary())

if __name__ == "__main__":
    unittest.main()


class FrameOsSessionTests(unittest.TestCase):
    def test_frame_os_minutes_per_decision(self):
        from gfg_plugin.session_stats import SessionStats
        st = SessionStats()
        st.start("k", 0.0)
        t = 0.0
        for level, n in (("calm", 120), ("boost", 30), ("rest", 60), (None, 30)):
            for _ in range(n):
                t += 1.0
                st.add(t, output=90, real=30, tdp=10, draw=9, reference_w=15, frame_os=level)
        self.assertEqual(st.summary()["frame_os"], {"calm": 2.0, "rest": 1.0, "boost": 0.5})

    def test_frame_os_benefit_is_kept_for_the_session_summary(self):
        st = SessionStats()
        st.start("k", 0.0)
        early = {"ready": False, "response_pct": 99.0}
        late = {"ready": True, "estimate": False, "response_pct": 41.0, "frames_pct": 12.0, "energy_pct": 8.0}
        for t in range(1, 61):
            st.add(float(t), output=90, real=30, tdp=10, draw=9, reference_w=15, frame_os="calm",
                   benefit=early if t < 30 else late)
        st.add(61.0, output=90, real=30, tdp=10, draw=9, reference_w=15, frame_os=None, benefit=None)
        self.assertEqual(st.summary()["frame_os_benefit"],
                         {"response": 41.0, "frames": 12.0, "energy": 8.0, "estimate": False})
        plain = SessionStats()
        plain.start("k", 0.0)
        for t in range(1, 61):
            plain.add(float(t), output=90, real=30, tdp=10, draw=9, reference_w=15)
        self.assertNotIn("frame_os_benefit", plain.summary())
