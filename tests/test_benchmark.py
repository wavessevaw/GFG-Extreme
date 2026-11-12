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
        self.assertFalse(self.b.measuring, "the game keeps its settings while the menu is open")
        run(self.b, self.clock, benchmark.SETTLE_S + 2)
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
            run(self.b, self.clock, benchmark.SETTLE_S + 2)
            run(self.b, self.clock, 2, **kw)
            self.assertEqual(self.b.state, "cancelled", kw)
            self.assertEqual(self.b.panel(), "cancelled")

    def test_accept_returns_the_result_decline_drops_it(self):
        for accept in (True, False):
            self.b.start(7, True)
            run(self.b, self.clock, benchmark.SETTLE_S + benchmark.DURATION_S + 3)
            res = self.b.answer(accept)
            self.assertEqual(res is not None, accept)
            self.assertEqual(self.b.state, "idle")

    def test_menu_left_open_calls_it_off(self):
        self.b.start(7, True)
        run(self.b, self.clock, benchmark.WAIT_MAX_S + 1, steam_ui=True)
        self.assertEqual(self.b.state, "cancelled")

    def test_ceiling_never_reached_still_measures(self):
        self.b.start(7, True)
        run(self.b, self.clock, benchmark.SETTLE_MAX_S + 2, at_ceiling=False)
        self.assertEqual(self.b.state, "running")

    def test_no_frames_cancels(self):
        self.b.start(7, True)
        run(self.b, self.clock, benchmark.SETTLE_S + 2)
        run(self.b, self.clock, benchmark.NO_FRAMES_S + 1, real=None)
        self.assertEqual(self.b.state, "cancelled")

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



class PowerDefaultsTest(unittest.TestCase):
    def test_split_and_gpu_clock_off_from_schema_4(self):
        from gfg_plugin import settings
        self.assertEqual(settings.normalize({})["power"], {"enabled": True, "split": False, "gpu_clock": False})
        self.assertEqual(settings.normalize({"schema": 4, "power": {}})["power"],
                         {"enabled": True, "split": False, "gpu_clock": False})
        # Schema 3 was previously forced off; the upgrade must preserve the user's saved choices.
        old = settings.normalize({"schema": 3, "power": {"enabled": True, "split": True, "gpu_clock": True}})
        self.assertEqual(old["power"], {"enabled": True, "split": True, "gpu_clock": True})
        earlier = settings.normalize({"schema": 2, "power": {"split": True, "gpu_clock": True}})
        self.assertFalse(earlier["power"]["split"] or earlier["power"]["gpu_clock"])
        new = settings.normalize({"schema": 4, "power": {"enabled": True, "split": True, "gpu_clock": False}})
        self.assertTrue(new["power"]["split"])


if __name__ == "__main__":
    unittest.main()
