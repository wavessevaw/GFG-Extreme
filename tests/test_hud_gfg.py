import unittest

import helpers  # noqa: F401

from gfg_plugin.kedavra import hud


class GfgHudTest(unittest.TestCase):
    def test_rings_by_detail(self):
        st = {"state": "active", "refresh_ns": 11111111, "multiplier": 4, "base_fps": 24, "gpu_us_avg": 1800, "time_ns": 2e9}
        rates = {"flips": 90, "sources": 24, "real": 24, "gen": 66, "repeat": 0}
        extra = {"tdp_w": 9, "draw_w": 8.4, "temp_c": 71, "managing": True, "ceiling_w": 15,
                 "battery": {"percent": 64, "external_power": False, "hours_left": 2.09}}
        labels = lambda d: [i["label"] for i in hud.gfg_items(st, rates, extra, d)]  # noqa: E731
        self.assertEqual(labels("minimal"), ["FPS", "CAP 24"])
        self.assertEqual(labels("standard"), ["FPS", "TDP W", "CAP 24", "TEMP C", "BATTERY H", "PACE %"])
        items = {i["label"]: i for i in hud.gfg_items(st, rates, extra, "standard")}
        self.assertEqual(items["BATTERY H"]["text"], "2:05")
        self.assertAlmostEqual(items["BATTERY H"]["frac"], 0.64)
        self.assertEqual(items["TDP W"]["text"], "9.0")
        ac = hud.battery_ring({"percent": 80, "external_power": True})
        self.assertEqual(ac["text"], "AC")
        self.assertEqual(items["CAP 24"]["text"], "x3.75")
        self.assertEqual(items["TEMP C"]["text"], "71")
        items = hud.gfg_items(st, rates, extra, "standard")
        w, h, px = hud.render(st, rates, hud.scale_for(800), items)
        self.assertEqual(len(px), w * h * 4)


class HudSizeTest(unittest.TestCase):
    def test_smaller_and_every_scale_has_glyphs_and_wolf(self):
        self.assertEqual(hud.scale_for(800), 0.88)
        self.assertEqual(hud.scale_for(1600), 1.76)
        for s in hud.SCALES:
            for style in ("fps", "val", "sub", "lab"):
                self.assertIn("0", hud._atlas()[f"{style}@{s}"]["glyphs"])
            self.assertIsNotNone(hud._logo(s))
