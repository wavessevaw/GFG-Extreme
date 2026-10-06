import tempfile, unittest
from pathlib import Path
from py_modules.gfg_plugin import governor_hud as hud


class HudTests(unittest.TestCase):
    def test_normalize_rejects_unknown(self):
        self.assertEqual(hud.normalize("x", "y"), ("standard", "top-right"))
        self.assertEqual(hud.normalize("MINIMAL", "top-left"), ("minimal", "top-left"))

    def test_status_line_variants(self):
        s = {"enabled": True, "state": "LOCKED", "telemetry": {"real": {"median": 44.6}, "output": {"median": 90.2}, "latest": {"effective_multiplier": 2.01}}, "power": {"owned": False, "observed_tdp_w": 9.2}, "active_point": {"render_scale_pct": 90}, "effort": {"level": "medium"}}
        self.assertEqual(hud.status_line(s), "x2 | 45 > 90 | scale 90% | 9W | medium")
        self.assertEqual(hud.status_line(s, "minimal"), "x2 | 45 > 90")
        self.assertEqual(hud.status_line(s, "detailed"), "x2 | 45 > 90 | scale 90% | 9W | medium | locked")
        self.assertEqual(hud.status_line({"enabled": False}), "GFG off")

    def test_status_line_without_telemetry(self):
        self.assertEqual(hud.status_line({"enabled": True, "state": "PROBE"}), "GFG | scale 100% | TDP n/a")

    def test_config_has_no_cpu_and_always_frametime(self):
        p = Path("/x/status.txt")
        for preset in hud.PRESETS:
            cfg = hud.mangohud_config(preset, "top-right", p)
            self.assertNotIn("cpu", cfg)
            self.assertIn("\nframetime\n", cfg)
            self.assertIn("exec=cat /x/status.txt", cfg)
        self.assertNotIn("gpu_stats", hud.mangohud_config("standard", "top-right", p))
        self.assertIn("gpu_stats", hud.mangohud_config("detailed", "top-right", p))
        self.assertIn("position=top-left", hud.mangohud_config("minimal", "top-left", p))
        self.assertIn("position=top-right", hud.mangohud_config("standard", "bogus", p))

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
