import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "py_modules"))

from gfg_plugin.governor_core import OperatingPointPlanner, TrialLadder  # noqa: E402
from gfg_plugin.governor_device import detect_model, target_for  # noqa: E402


class DeviceTargetTests(unittest.TestCase):
    def dmi(self, product):
        root = Path(tempfile.mkdtemp())
        (root / "product_name").write_text(product + "\n")
        return root

    def test_dmi_models(self):
        self.assertEqual(detect_model(self.dmi("Galileo"))["model"], "oled")
        self.assertEqual(detect_model(self.dmi("Jupiter"))["model"], "lcd")
        self.assertEqual(detect_model(self.dmi("ROG Ally"))["model"], "unknown")
        self.assertEqual(detect_model(Path("/nonexistent"))["model"], "unknown")

    def test_targets(self):
        self.assertEqual(target_for("oled", external=False)["target"], 90)
        self.assertEqual(target_for("lcd", external=False)["target"], 60)
        self.assertEqual(target_for("oled", external=True)["target"], 60)
        self.assertEqual(target_for("lcd", external=True)["target"], 60)

    def test_unknown_device_uses_panel_rates(self):
        self.assertEqual(target_for("unknown", external=False, valid_rates=[60, 90])["target"], 90)
        self.assertEqual(target_for("unknown", external=False, valid_rates=[40, 60])["target"], 60)
        self.assertEqual(target_for("unknown", external=False)["target"], 60)

    def test_candidates_follow_target_and_never_offer_x4_x5(self):
        for target, keys in (
            (90, ["native90", "72x1.25", "60x1.5", "51x1.75", "45x2", "40x2.25", "36x2.5", "45x2-s90", "45x2-s80", "33x2.75", "30x3", "30x3-s90", "30x3-s80"]),
            (60, ["native60", "48x1.25", "40x1.5", "34x1.75", "30x2", "27x2.25", "24x2.5", "30x2-s90", "30x2-s80", "22x2.75", "20x3-degraded"]),
        ):
            points = OperatingPointPlanner.candidates(target_output_fps=target)
            self.assertEqual([p.key for p in points][:len(keys)], keys)
            self.assertEqual(len(points), len(keys))
            self.assertTrue(all(p.multiplier <= 3 and p.target_output_fps == target for p in points))
        self.assertEqual(TrialLadder(target_output_fps=60).candidates()[0].key, "native60")


if __name__ == "__main__":
    unittest.main()
