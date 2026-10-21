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


if __name__ == "__main__":
    unittest.main()
