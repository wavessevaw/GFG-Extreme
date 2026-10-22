import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "py_modules"))

from gfg_plugin.governor_device import target_for  # noqa: E402


class LcdTargetTest(unittest.TestCase):
    def test_stock_lcd_is_60(self):
        self.assertEqual(target_for("lcd", external=False, current_hz=60)["target"], 60)

    def test_unlocked_lcd_follows_its_panel(self):
        # user, 3.1.0: some LCD panels are unlocked to about 75 Hz
        self.assertEqual(target_for("lcd", external=False, current_hz=75)["target"], 75)

    def test_dock_stays_60(self):
        self.assertEqual(target_for("lcd", external=True, current_hz=75)["target"], 60)


if __name__ == "__main__":
    unittest.main()
