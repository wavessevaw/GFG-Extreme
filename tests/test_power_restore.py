import tempfile
import unittest
from pathlib import Path

import helpers  # noqa: F401

from gfg_plugin.governor_power import SteamDeckPowerActuator


class RestoreFailureTest(unittest.TestCase):
    def test_failed_restore_keeps_the_users_caps_for_the_next_claim(self):
        with tempfile.TemporaryDirectory() as d:
            fast, slow = Path(d, "power1_cap"), Path(d, "power2_cap")
            fast.write_text("15000000\n")
            slow.write_text("15000000\n")
            a = SteamDeckPowerActuator(helper=lambda: None)
            a._fast_path, a._slow_path = fast, slow
            a.state.available = True
            self.assertTrue(a._claim()["owned"])
            fast.write_text("10000000\n")   # GFG lowered the TDP
            slow.write_text("10000000\n")
            a.state.expected_fast_uw = a.state.expected_slow_uw = 10_000_000
            a._apply = lambda *_, **__: ("write-failed", "injected")
            self.assertFalse(a.restore_if_owned()["restored"])
            a._claim()                         # the next game
            self.assertEqual(a.state.initial_slow_uw, 15_000_000)
            self.assertEqual(a.state.initial_fast_uw, 15_000_000)


class IntentJournalTest(unittest.TestCase):
    """Governor 2.0 journal: a plugin that dies with the TDP lowered gives it back next time."""

    def rig(self, d, marker=True):
        fast, slow = Path(d, "power1_cap"), Path(d, "power2_cap")
        fast.write_text("15000000\n")
        slow.write_text("15000000\n")
        a = SteamDeckPowerActuator(helper=lambda: None, marker=Path(d, "tdp-cap.json") if marker else None)
        a._fast_path, a._slow_path = fast, slow
        a._direct_possible = lambda: True
        a.state.available = True
        return a, fast, slow

    def test_crash_with_lowered_tdp_is_recovered_on_next_claim(self):
        with tempfile.TemporaryDirectory() as d:
            a, fast, slow = self.rig(d)
            a._claim()
            self.assertTrue(a.set_tdp_w(10)["success"])
            self.assertTrue(Path(d, "tdp-cap.json").exists())
            b = SteamDeckPowerActuator(helper=lambda: None, marker=Path(d, "tdp-cap.json"))  # plugin restarted
            b._fast_path, b._slow_path, b.state.available = fast, slow, True
            b._direct_possible = lambda: True
            b._claim()
            self.assertEqual(slow.read_text().strip(), "15000000")
            self.assertEqual(b.state.initial_slow_uw, 15_000_000)
            self.assertFalse(Path(d, "tdp-cap.json").exists())

    def test_caps_changed_by_someone_else_stay(self):
        with tempfile.TemporaryDirectory() as d:
            a, fast, slow = self.rig(d)
            a._claim()
            a.set_tdp_w(10)
            fast.write_text("8000000\n")   # Steam's slider after the crash
            slow.write_text("8000000\n")
            b = SteamDeckPowerActuator(helper=lambda: None, marker=Path(d, "tdp-cap.json"))
            b._fast_path, b._slow_path, b.state.available = fast, slow, True
            b._claim()
            self.assertEqual(slow.read_text().strip(), "8000000")
            self.assertEqual(b.state.initial_slow_uw, 8_000_000)

    def test_clean_restore_clears_the_marker(self):
        with tempfile.TemporaryDirectory() as d:
            a, _, slow = self.rig(d)
            a._claim()
            a.set_tdp_w(9)
            self.assertTrue(a.restore_if_owned()["restored"])
            self.assertEqual(slow.read_text().strip(), "15000000")
            self.assertFalse(Path(d, "tdp-cap.json").exists())

    def test_no_marker_no_write(self):
        with tempfile.TemporaryDirectory() as d:
            a, _, slow = self.rig(d)
            a.marker = Path(d, "missing-dir-file", "x", "tdp-cap.json")
            Path(d, "missing-dir-file").write_text("not a dir")
            a._claim()
            self.assertFalse(a.set_tdp_w(10)["success"])
            self.assertEqual(slow.read_text().strip(), "15000000")


if __name__ == "__main__":
    unittest.main()
