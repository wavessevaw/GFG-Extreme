import unittest

from helpers import Clock

from gfg_plugin import benchmark
from gfg_plugin.benchmark import Benchmark, strategy
from gfg_plugin.kedavra import hud


def sample(**kw):
    s = {"app": 7, "game": True, "steam_ui": False, "real": 47.0, "gpu": 96, "cpu": 58, "draw_w": 15.0,
         "temp_c": 71, "at_ceiling": True, "refresh": 90, "dock": False, "above_x3": False}
    s.update(kw)
    return s


def run(b, clock, seconds, **kw):
    for _ in range(int(seconds)):
        clock.t += 1
        b.tick(sample(**kw))


class BenchmarkTest(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.b = Benchmark(clock=self.clock)

    def test_needs_a_game(self):
        self.assertFalse(self.b.start(None, False)["ok"])
        self.assertEqual(self.b.state, "idle")

    def test_waits_for_quick_access_then_measures_20_s(self):
        self.b.start(7, True)
        run(self.b, self.clock, 10, steam_ui=True)
        self.assertEqual(self.b.state, "waiting")
        run(self.b, self.clock, benchmark.SETTLE_S + 1)
        self.assertEqual(self.b.state, "running")
        self.assertEqual(self.b.panel(), "measuring")
        run(self.b, self.clock, benchmark.DURATION_S + 1)
        self.assertEqual(self.b.state, "done")
        self.assertEqual(self.b.panel(), "done")
        self.assertEqual(self.b.result["point"], 40)       # 47 fps at 15 W: 40 holds with generation on
        self.assertEqual(self.b.result["medians"]["real"], 47.0)

    def test_steam_menu_pause_or_game_change_cancels(self):
        for kw in ({"steam_ui": True}, {"real": 0.0}, {"app": 8}):
            self.b.start(7, True)
            run(self.b, self.clock, benchmark.SETTLE_S + 1)
            run(self.b, self.clock, 2, **kw)
            self.assertEqual(self.b.state, "cancelled", kw)
            self.assertEqual(self.b.panel(), "cancelled")

    def test_accept_returns_the_result_decline_drops_it(self):
        for accept in (True, False):
            self.b.start(7, True)
            run(self.b, self.clock, benchmark.SETTLE_S + benchmark.DURATION_S + 2)
            res = self.b.answer(accept)
            self.assertEqual(res is not None, accept)
            self.assertEqual(self.b.state, "idle")

    def test_decline_cancels_a_run(self):
        self.b.start(7, True)
        self.assertIsNone(self.b.answer(False))
        self.assertFalse(self.b.measuring)

    def test_strategy_follows_base_fps(self):
        self.assertEqual(strategy(60, 15, 90, False, False)["point"], 45)
        self.assertEqual(strategy(38, 15, 90, False, False)["point"], 35)
        low = strategy(25, 15, 90, False, False)
        self.assertEqual(low["point"], 30)               # the lowest Autopilot point without ×3.75
        self.assertFalse(low["holds"])

    def test_hud_panel_fits_the_atlas_and_size(self):
        for scale in hud.SCALES:
            for panel, view in (("measuring", {"seconds_left": 12, "live": {"real": 47, "gpu": 96, "cpu": 58, "draw_w": 15.0, "temp_c": 71}}),
                                ("done", {"result": {"point": 40, "multiplier": "x2.25", "watts": 11}}),
                                ("cancelled", {"reason": "the Steam menu opened"})):
                w, h, px = hud.render_message(panel, view, scale)
                self.assertEqual(len(px), w * h * 4)
                self.assertLessEqual(len(px), 1 << 20)


if __name__ == "__main__":
    unittest.main()
