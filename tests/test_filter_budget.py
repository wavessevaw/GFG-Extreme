import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "py_modules"))
sys.path.insert(0, str(ROOT))

from gfg_plugin.filter_budget import FilterBudget, shed  # noqa: E402
from sandbox.run import make_rig, play  # noqa: E402
from sandbox.vdeck import VGame  # noqa: E402

FULL = {"effects": ["vibrance", "clarity"], "sharpen": "dls", "sharpness": 0.4, "denoise": 0.17, "aa": "smaa"}


class Clock:
    t = 0.0

    def __call__(self):
        return self.t


class FilterBudgetTest(unittest.TestCase):
    def test_levels(self):
        self.assertEqual(shed(FULL, 0), FULL)
        light = shed(FULL, 1)
        self.assertEqual((light["effects"], light["sharpen"], light["aa"]), (["vibrance"], "cas", "none"))
        off = shed(FULL, 2)
        self.assertEqual((off["effects"], off["sharpen"], off["aa"]), ([], "none", "none"))

    def test_sheds_while_starved_and_comes_back(self):
        c = Clock()
        b = FilterBudget(clock=c)
        levels = []
        for _ in range(45):
            levels.append(b.tick(app=1, active=True, gpu_busy=99.0, starved=True))
            c.t += 1
        self.assertEqual((levels[19], levels[20], levels[41]), (0, 1, 2))
        for _ in range(91):
            b.tick(app=1, active=True, gpu_busy=60.0, starved=False)
            c.t += 1
        self.assertEqual(b.level, 1)
        self.assertEqual(b.tick(app=2, active=True, gpu_busy=99.0, starved=True), 0)  # a new game

    def test_not_starved_keeps_filters(self):
        c = Clock()
        b = FilterBudget(clock=c)
        for _ in range(100):
            b.tick(app=1, active=True, gpu_busy=99.0, starved=False)
            c.t += 1
        self.assertEqual(b.level, 0)

    def test_heavy_game_sheds_in_the_service(self):
        rig = make_rig(VGame("g", 26.0), objective="autopilot")
        rig.settings.data["profiles"]["default"]["filters"] = dict(FULL)
        play(rig, 300)
        self.assertEqual(rig.engine.vars["kfg_post"], "")
        quality = make_rig(VGame("g", 26.0), objective="quality")
        quality.settings.data["profiles"]["default"]["filters"] = dict(FULL)
        play(quality, 300)
        self.assertNotEqual(quality.engine.vars["kfg_post"], "")


if __name__ == "__main__":
    unittest.main()
