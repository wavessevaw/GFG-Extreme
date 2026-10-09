import tempfile, unittest
from pathlib import Path
from py_modules.gfg_plugin import governor_hud as hud


class HudTests(unittest.TestCase):
    def test_normalize_rejects_unknown(self):
        self.assertEqual(hud.normalize("x", "y"), ("standard", "top-right"))
        self.assertEqual(hud.normalize("MINIMAL", "top-left"), ("minimal", "top-left"))

    def test_status_line_variants(self):
        s = {"enabled": True, "state": "LOCKED", "telemetry": {"real": {"median": 44.6}, "output": {"median": 90.2}, "latest": {"effective_multiplier": 2.01}}, "power": {"owned": False, "observed_tdp_w": 9.2}, "active_point": {"render_scale_pct": 90}, "effort": {"level": "medium"}, "battery": {"minutes_left": 125}}
        self.assertEqual(hud.status_line(s), "90 FPS  x2  (45)  sc90  9W  2h05  med")
        self.assertEqual(hud.status_line(s, "minimal"), "90 FPS  x2  (45)")
        self.assertEqual(hud.status_line(s, "detailed"), "90 FPS  x2  (45)  sc90  9W  2h05  med  locked")
        self.assertEqual(hud.status_line({"enabled": False}), "GFG off")

    def test_measured_draw_is_shown_next_to_the_limit(self):
        line = hud.status_line({"enabled": True, "power": {"observed_tdp_w": 18.0, "draw_w": 14.6}})
        self.assertIn("TDP 18W  APU 15W", line)

    def test_fractional_multiplier_is_shown_to_the_nearest_quarter(self):
        base = {"enabled": True, "state": "LOCKED", "telemetry": {"real": {"median": 60.0}, "output": {"median": 90.0}, "latest": {"effective_multiplier": 1.47}}}
        self.assertTrue(hud.status_line(base, "minimal").startswith("90 FPS  x1.5  (60)"))
        base["telemetry"]["output"]["median"] = 121.0
        self.assertTrue(hud.status_line(base, "minimal").startswith("121 FPS  x2  "))

    def test_multiplier_follows_medians_not_the_last_sample(self):
        # Field log: active point 45x2, last sample from a menu with generation stopped.
        s = {"enabled": True, "telemetry": {"summary": {"real": {"median": 44.0}, "output": {"median": 88.0},
                                                        "multiplier": {"median": 2.0},
                                                        "latest": {"effective_multiplier": 1.0}}}}
        self.assertEqual(hud.status_line(s, "minimal"), "88 FPS  x2  (44)")
        s["telemetry"]["summary"]["real"] = {"median": None}
        self.assertEqual(hud.status_line(s, "minimal"), "88 FPS  x2")

    def test_hot_apu_is_flagged_outside_minimal(self):
        s = {"enabled": True, "state": "LOCKED", "diagnosis": {"thermal": "hot"}}
        self.assertIn("HOT", hud.status_line(s))
        self.assertNotIn("HOT", hud.status_line(s, "minimal"))
        s["diagnosis"]["thermal"] = "heating"
        self.assertNotIn("HOT", hud.status_line(s))

    def test_battery_time_omitted_when_unknown(self):
        s = {"enabled": True, "state": "LOCKED", "battery": {"minutes_left": None}}
        self.assertEqual(hud.status_line(s), "GFG  sc100  TDPn/a")

    def test_status_line_marks_extreme(self):
        line = hud.status_line({"enabled": True, "active_point": {"render_scale_pct": 80},
                                "extreme": {"enabled": True, "applied": {"render_pct": 80}}})
        self.assertIn("sc80  EXT", line)
        self.assertNotIn("EXT", hud.status_line({"enabled": True, "extreme": {"enabled": False}}))

    def test_extreme_scale_is_confirmed_not_requested(self):
        status = {"enabled": True, "active_point": {"render_scale_pct": 80},
                  "extreme": {"enabled": True, "requested": {"render_pct": 80}}}
        self.assertIn("sc?  EXT", hud.status_line(status))
        status["extreme"]["applied"] = {"render_pct": 100}
        self.assertIn("sc100  EXT", hud.status_line(status))
        self.assertNotIn("sc80", hud.status_line(status))

    def test_status_line_without_telemetry(self):
        self.assertEqual(hud.status_line({"enabled": True, "state": "PROBE"}), "GFG  sc100  TDPn/a")

    def test_config_has_no_cpu_and_unstretched_bar(self):
        p = Path("/x/status.txt")
        for preset in hud.PRESETS:
            cfg = hud.mangohud_config(preset, "top-right", p)
            self.assertNotIn("cpu", cfg)
            self.assertIn("\nframetime\n", cfg)
            self.assertIn("\nhorizontal\n", cfg)
            self.assertIn("\nhorizontal_stretch=0\n", cfg)
            self.assertIn("exec=cat /x/status.txt", cfg)
            self.assertLess(cfg.index("exec="), cfg.index("\nfps\n"))
        self.assertNotIn("gpu_stats", hud.mangohud_config("standard", "top-right", p))
        self.assertIn("gpu_stats", hud.mangohud_config("detailed", "top-right", p))
        self.assertIn("position=top-left", hud.mangohud_config("minimal", "top-left", p))
        self.assertIn("position=top-right", hud.mangohud_config("standard", "bogus", p))

    def test_generated_fps_replaces_mangohud_counter(self):
        p = Path("/x/status.txt")
        cfg = hud.mangohud_config("standard", "bottom-right", p, generated_fps=True)
        self.assertNotIn("\nfps\n", cfg)
        self.assertNotIn("\nframetime\n", cfg)
        self.assertIn("position=bottom-right", cfg)
        s = {"enabled": True, "telemetry": {"snapshot": {"sample_age_ms": 100, "latest": {"output_fps": 90}}, "summary": {"output": {"median": 90.0}}}}
        self.assertEqual(hud.output_fps(s), 90.0)
        self.assertIsNone(hud.output_fps({"enabled": True}))
        self.assertIsNone(hud.output_fps({**s, "enabled": False}))

    def test_writer_is_idempotent(self):
        with tempfile.TemporaryDirectory() as d:
            w = hud.HudWriter(Path(d))
            w.MIN_REWRITE_S = 0.0  # rate limit tested separately
            self.assertTrue(w.write_status({"enabled": False}))
            self.assertFalse(w.write_status({"enabled": False}))
            cfg = w.activate("standard", "top-left")
            self.assertTrue(cfg.is_file())
            w.deactivate(); w.deactivate()
            # Hidden, not removed: MangoHud stays loaded and re-reads it.
            self.assertEqual(cfg.read_text(), hud.HIDDEN_CONFIG)
            w.activate("standard", "top-left")
            self.assertIn("no_display=0", cfg.read_text())
            self.assertTrue(w.config_exists())
            w.remove()
            self.assertFalse(cfg.exists())
            self.assertEqual(hud.status_path(Path(d)).read_text(), "GFG off\n")

    def test_burst_of_overlay_changes_reaches_mangohud_as_one_rewrite(self):
        """Field log: six changes in eight seconds, then the game crashed."""
        with tempfile.TemporaryDirectory() as d:
            now = {"t": 1000.0}
            w = hud.HudWriter(Path(d), clock=lambda: now["t"])
            cfg = w.activate("standard", "top-left")
            first = cfg.read_text()
            writes = []
            for preset, pos in (("detailed", "top-left"), ("standard", "top-left"), ("minimal", "top-left"),
                                ("standard", "top-left"), ("standard", "top-right"), ("standard", "bottom-right")):
                now["t"] += 1.3
                w.activate(preset, pos)
                writes.append(cfg.read_text())
            rewrites = sum(1 for a, b in zip([first] + writes, writes) if a != b)
            self.assertLessEqual(rewrites, 1, "at most one live rewrite per 5 s inside the burst (was 6)")
            self.assertIsNotNone(w.pending)
            now["t"] += w.MIN_REWRITE_S
            w.activate("standard", "bottom-right")      # the loop re-applies the current state
            self.assertIn("position=bottom-right", cfg.read_text())   # only the final state
            self.assertIsNone(w.pending)

    def test_pending_visible_config_is_never_published_after_the_hud_is_turned_off(self):
        """PR #35 review: a stale pending config must not reach MangoHud after disable/remove."""
        with tempfile.TemporaryDirectory() as d:
            now = {"t": 1000.0}
            w = hud.HudWriter(Path(d), clock=lambda: now["t"])
            cfg = w.activate("standard", "top-left")
            now["t"] += 1.0
            w.activate("detailed", "bottom-right")       # rate-limited: pending
            self.assertIsNotNone(w.pending)
            now["t"] += 1.0
            w.remove()                                   # HUD off before the interval ends
            self.assertIsNone(w.pending)
            now["t"] += w.MIN_REWRITE_S * 3
            self.assertFalse(cfg.exists())
            w.deactivate()                               # later desired state: hidden
            self.assertEqual(cfg.read_text(), hud.HIDDEN_CONFIG)
            self.assertNotIn("bottom-right", cfg.read_text())

    def test_newer_desired_state_replaces_an_older_pending_one(self):
        with tempfile.TemporaryDirectory() as d:
            now = {"t": 1000.0}
            w = hud.HudWriter(Path(d), clock=lambda: now["t"])
            cfg = w.activate("standard", "top-left")
            now["t"] += 1.0
            w.activate("detailed", "bottom-right")
            now["t"] += 1.0
            w.deactivate()                               # hidden is now what is wanted
            now["t"] += w.MIN_REWRITE_S
            w.deactivate()
            self.assertEqual(cfg.read_text(), hud.HIDDEN_CONFIG)

    def test_unchanged_config_is_never_rewritten(self):
        with tempfile.TemporaryDirectory() as d:
            now = {"t": 0.0}
            w = hud.HudWriter(Path(d), clock=lambda: now["t"])
            w.activate("standard", "top-left")
            now["t"] += 100
            self.assertFalse(w._write_config(hud.active_config_path(Path(d)).read_text()))


if __name__ == "__main__":
    unittest.main()


class FrameOsHudTests(unittest.TestCase):
    def test_frame_os_word(self):
        fo = {"enabled": True, "acting": True, "telemetry": {"live": True}, "decision": {"level": "boost", "real_hz": 45.0}}
        self.assertEqual(hud.frame_os_word(fo), "FOS verifying 45")
        self.assertEqual(hud.frame_os_word({**fo, "acting": False}), "FOS boost? 45")
        self.assertEqual(hud.frame_os_word({**fo, "telemetry": {"live": False}}), "")
        self.assertEqual(hud.frame_os_word({"enabled": False}), "")
        line = hud.status_line({"enabled": True, "power": {"observed_tdp_w": 9.0}, "frame_os": fo})
        self.assertTrue(line.endswith("FOS boost 45"))
        self.assertNotIn("FOS", hud.status_line({"enabled": True, "frame_os": fo}, "minimal"))

class HudTelemetryRegressionTests(unittest.TestCase):
    def test_text_uses_latest_interval_not_old_scene_medians(self):
        status = {"enabled": True, "telemetry": {
            "snapshot": {"sample_age_ms": 100, "latest": {"real_fps": 30, "output_fps": 60}},
            "summary": {"real": {"median": 45}, "output": {"median": 90}}}}
        self.assertEqual(hud.status_line(status, "minimal"), "60 FPS  x2  (30)")
        status["telemetry"]["snapshot"]["sample_age_ms"] = 3000
        self.assertNotIn("FPS", hud.status_line(status, "minimal"))
        self.assertIsNone(hud.output_fps(status))

    def test_hud_only_shows_live_fps_without_enabling_governor(self):
        status = {"enabled": False, "telemetry": {"snapshot": {
            "sample_age_ms": 100, "latest": {"real_fps": 30, "output_fps": 90}}}}
        self.assertEqual(hud.status_line(status, "minimal"), "90 FPS  x3  (30)")
        self.assertEqual(hud.output_fps(status), 90)
        status["telemetry"]["snapshot"]["sample_age_ms"] = 5000
        self.assertEqual(hud.status_line(status), "GFG off")

    def test_bad_numbers_do_not_break_fallback(self):
        for bad in (float("nan"), float("inf"), True, -1, "bad"):
            status = {"enabled": True, "telemetry": {"real": {"median": bad}, "output": {"median": bad}},
                      "power": {"observed_tdp_w": bad, "draw_w": bad},
                      "battery": {"minutes_left": bad}, "effort": {"level": "unknown"},
                      "active_point": {"render_scale_pct": bad}}
            self.assertNotIn("FPS", hud.status_line(status))
            self.assertIsNone(hud.output_fps(status))
