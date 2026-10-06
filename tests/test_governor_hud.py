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

    def test_battery_time_omitted_when_unknown(self):
        s = {"enabled": True, "state": "LOCKED", "battery": {"minutes_left": None}}
        self.assertEqual(hud.status_line(s), "GFG  sc100  TDPn/a")

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
        s = {"enabled": True, "telemetry": {"snapshot": {}, "summary": {"output": {"median": 90.0}}}}
        self.assertEqual(hud.output_fps(s), 90.0)
        self.assertIsNone(hud.output_fps({"enabled": True}))
        self.assertIsNone(hud.output_fps({**s, "enabled": False}))

    def test_writer_is_idempotent(self):
        with tempfile.TemporaryDirectory() as d:
            w = hud.HudWriter(Path(d))
            self.assertTrue(w.write_status({"enabled": False}))
            self.assertFalse(w.write_status({"enabled": False}))
            cfg = w.activate("standard", "top-left")
            self.assertTrue(cfg.is_file())
            w.deactivate(); w.deactivate()
            self.assertFalse(cfg.exists())
            self.assertEqual(hud.status_path(Path(d)).read_text(), "GFG off\n")


if __name__ == "__main__":
    unittest.main()
