import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "py_modules"))

from gfg_plugin.governor_power import SteamDeckPowerActuator


def write(path: Path, value):
    path.write_text(f"{value}\n", encoding="utf-8")


class GovernorPowerActuatorTests(unittest.TestCase):
    def make_hwmon(self, root: Path):
        h = root / "hwmon" / "hwmon0"
        h.mkdir(parents=True)
        write(h / "power1_label", "fastPPT")
        write(h / "power2_label", "slowPPT")
        write(h / "power1_cap", 18000000)
        write(h / "power2_cap", 15000000)
        write(h / "power1_cap_min", 3000000)
        write(h / "power2_cap_min", 3000000)
        write(h / "power1_cap_max", 20000000)
        write(h / "power2_cap_max", 20000000)
        return h

    def test_discover_claim_reduce_restore(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            h = self.make_hwmon(root)
            actuator = SteamDeckPowerActuator(drm_root=root / "drm", hwmon_root=root / "hwmon")
            self.assertTrue(actuator.discover()["available"])
            claimed = actuator.claim()
            self.assertTrue(claimed["owned"])
            result = actuator.set_tdp_w(10)
            self.assertTrue(result["success"])
            self.assertEqual(int((h / "power2_cap").read_text()), 10000000)
            self.assertEqual(int((h / "power1_cap").read_text()), 12000000)
            restored = actuator.restore_if_owned()
            self.assertTrue(restored["restored"])
            self.assertEqual(int((h / "power2_cap").read_text()), 15000000)

    def test_external_change_releases_ownership_and_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            h = self.make_hwmon(root)
            actuator = SteamDeckPowerActuator(drm_root=root / "drm", hwmon_root=root / "hwmon")
            actuator.discover(); actuator.claim(); actuator.set_tdp_w(10)
            write(h / "power2_cap", 9000000)  # QAM / another tool changed it
            status = actuator.verify_ownership()
            self.assertFalse(status["owned"])
            self.assertTrue(status["external_change"])
            restored = actuator.restore_if_owned()
            self.assertFalse(restored["restored"])
            self.assertEqual(int((h / "power2_cap").read_text()), 9000000)

    def test_never_raises_above_claimed_ceiling(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            h = self.make_hwmon(root)
            actuator = SteamDeckPowerActuator(drm_root=root / "drm", hwmon_root=root / "hwmon")
            actuator.discover(); actuator.claim()
            actuator.set_tdp_w(30)
            self.assertEqual(int((h / "power2_cap").read_text()), 15000000)
            self.assertEqual(int((h / "power1_cap").read_text()), 18000000)
