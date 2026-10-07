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

    def test_reports_measured_apu_draw(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            h = self.make_hwmon(root)
            write(h / "power2_average", 12345678)
            actuator = SteamDeckPowerActuator(drm_root=root / "drm", hwmon_root=root / "hwmon")
            status = actuator.discover()
            self.assertEqual(status["draw_w"], 12.35)
            self.assertEqual(status["observed_tdp_w"], 15.0)

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

    def test_budget_ceiling_allows_up_to_hardware_maximum_then_resets(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            h = self.make_hwmon(root)
            actuator = SteamDeckPowerActuator(drm_root=root / "drm", hwmon_root=root / "hwmon")
            actuator.discover(); actuator.claim()
            actuator.set_ceiling_w(25)              # clamped to the hardware maximum
            self.assertEqual(actuator.status()["ceiling_tdp_w"], 20.0)
            self.assertEqual(actuator.status()["initial_tdp_w"], 15.0, "the user's own limit, not the override")
            self.assertEqual(actuator.status()["maximum_tdp_w"], 20.0)
            actuator.set_tdp_w(18)
            self.assertEqual(int((h / "power2_cap").read_text()), 18000000)
            self.assertEqual(int((h / "power1_cap").read_text()), 20000000)  # fast keeps ratio, clamped
            actuator.set_ceiling_w(None)
            actuator.set_tdp_w(18)
            self.assertEqual(int((h / "power2_cap").read_text()), 15000000)
            actuator.restore_if_owned()
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


class PowerRestoreSafetyTests(GovernorPowerActuatorTests):
    """Audit 1.0.8: paths where the user's TDP was not put back."""

    def make(self, root):
        h = self.make_hwmon(root)
        actuator = SteamDeckPowerActuator(drm_root=root / "drm", hwmon_root=root / "hwmon")
        actuator.discover(); actuator.claim()
        return h, actuator

    def test_half_done_write_is_still_restored(self):
        with tempfile.TemporaryDirectory() as temp:
            h, actuator = self.make(Path(temp))
            original = actuator._write_value

            def fast_refused(path, value):
                if path.name == "power1_cap":
                    raise OSError("fast cap busy")
                original(path, value)
            actuator._write_value = fast_refused
            self.assertFalse(actuator.set_tdp_w(9)["success"])
            self.assertEqual(int((h / "power2_cap").read_text()), 9000000)   # slow was written
            actuator._write_value = original
            self.assertTrue(actuator.verify_ownership()["owned"], "our own write is not an outside change")
            self.assertTrue(actuator.restore_if_owned()["restored"])
            self.assertEqual(int((h / "power2_cap").read_text()), 15000000)

    def test_unverified_write_is_still_restored(self):
        with tempfile.TemporaryDirectory() as temp:
            h, actuator = self.make(Path(temp))
            original = actuator._write_value
            actuator._write_value = lambda path, value: original(path, value - 1000)  # cap reads off by 1 mW
            self.assertFalse(actuator.set_tdp_w(9)["success"])
            self.assertFalse(actuator.status()["owned"])
            actuator._write_value = original
            self.assertTrue(actuator.restore_if_owned()["restored"])
            self.assertEqual(int((h / "power2_cap").read_text()), 15000000)
            self.assertEqual(int((h / "power1_cap").read_text()), 18000000)

    def test_unverified_write_never_restores_over_another_tool(self):
        """Review 1.0.10: an outside write is exactly what makes our readback fail."""
        with tempfile.TemporaryDirectory() as temp:
            h, actuator = self.make(Path(temp))
            original = actuator._write_value
            actuator._write_value = lambda path, value: original(path, value - 1000)
            self.assertFalse(actuator.set_tdp_w(9)["success"])
            actuator._write_value = original
            write(h / "power2_cap", 10000000); write(h / "power1_cap", 12000000)   # QAM slider
            result = actuator.restore_if_owned()
            self.assertEqual((result["restored"], result["reason"]), (False, "external-change"))
            self.assertEqual(int((h / "power2_cap").read_text()), 10000000)

    def test_shutdown_waits_for_a_write_in_flight_and_refuses_later_ones(self):
        import threading
        import time as _time
        with tempfile.TemporaryDirectory() as temp:
            h, actuator = self.make(Path(temp))
            original = actuator._write_value

            def slow_write(path, value):
                _time.sleep(0.2)
                original(path, value)
            actuator._write_value = slow_write
            writer = threading.Thread(target=actuator.set_tdp_w, args=(9,))
            writer.start()
            _time.sleep(0.05)                           # the write is in flight
            self.assertTrue(actuator.shutdown()["restored"])
            writer.join()
            self.assertEqual(int((h / "power2_cap").read_text()), 15000000)
            self.assertFalse(actuator.set_tdp_w(8)["success"])
            self.assertEqual(int((h / "power2_cap").read_text()), 15000000)
            actuator.reopen()
            actuator.claim()
            self.assertTrue(actuator.set_tdp_w(8)["success"])
