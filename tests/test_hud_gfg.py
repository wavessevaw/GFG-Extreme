import unittest

import helpers  # noqa: F401

from gfg_plugin.kedavra import hud


class GfgHudTest(unittest.TestCase):
    def test_rings_by_detail(self):
        st = {"state": "active", "refresh_ns": 11111111, "multiplier": 4, "base_fps": 24, "gpu_us_avg": 1800, "time_ns": 2e9}
        rates = {"flips": 90, "sources": 24, "real": 24, "gen": 66, "repeat": 0}
        extra = {"tdp_w": 9, "draw_w": 8.4, "temp_c": 71, "managing": True, "ceiling_w": 15}
        labels = lambda d: [i["label"] for i in hud.gfg_items(st, rates, extra, d)]  # noqa: E731
        self.assertEqual(labels("minimal"), ["FPS", "CAP 24"])
        self.assertEqual(labels("standard"), ["FPS", "CAP 24", "PACE", "TDP AUTO", "APU"])
        self.assertEqual(labels("full")[-1], "GEN MS")
        items = hud.gfg_items(st, rates, extra, "full")
        self.assertEqual(items[1]["text"], "x3.75")
        self.assertEqual(items[3]["text"], "9W")
        self.assertEqual(items[4]["text"], "71C")
        w, h, px = hud.render(st, rates, 1.0, items)
        self.assertEqual(len(px), w * h * 4)
