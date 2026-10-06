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

    def test_reports_measured_apu_draw_and_raw_sensors(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            h = self.make_hwmon(root)
            write(h / "name", "amdgpu")
            write(h / "power2_average", 12345678)
            actuator = SteamDeckPowerActuator(drm_root=root / "drm", hwmon_root=root / "hwmon")
            status = actuator.discover()
            self.assertEqual(status["draw_w"], 12.35)
            self.assertEqual(status["observed_tdp_w"], 15.0)
            sensors = actuator.sensors()
            self.assertEqual(sensors["name"], "amdgpu")
            self.assertEqual(sensors["power2_average"], "12345678")
            self.assertEqual(sensors["power1_label"], "fastPPT")
            self.assertTrue(sensors["draw_path"].endswith("power2_average"))

    def test_draw_unknown_without_sensor(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.make_hwmon(root)
            actuator = SteamDeckPowerActuator(drm_root=root / "drm", hwmon_root=root / "hwmon")
            self.assertIsNone(actuator.discover()["draw_w"])

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

    def test_read_only_caps_are_reported_unavailable(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            h = self.make_hwmon(root)
            actuator = SteamDeckPowerActuator(
                drm_root=root / "drm", hwmon_root=root / "hwmon", access=lambda path, mode: False,
            )
            status = actuator.discover()
            self.assertFalse(status["available"])
            self.assertFalse(status["writable"])
            self.assertEqual(status["observed_tdp_w"], 15.0)
            self.assertFalse(actuator.claim()["owned"])
            self.assertEqual(int((h / "power2_cap").read_text()), 15000000)


class PowerJournalTests(unittest.TestCase):
    def test_every_write_is_journaled_with_result(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            GovernorPowerActuatorTests.make_hwmon(None, root)
            notes = []
            actuator = SteamDeckPowerActuator(drm_root=root / "drm", hwmon_root=root / "hwmon")
            actuator.journal = lambda kind, **f: notes.append((kind, f))
            actuator.discover(); actuator.claim(); actuator.set_tdp_w(10); actuator.restore_if_owned()
            self.assertEqual([k for k, _ in notes], ["tdp-claim", "tdp-write", "tdp-restore"])
            self.assertTrue(notes[1][1]["success"])
            self.assertEqual(notes[1][1]["observed_w"], 10.0)
