import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "py_modules"))

from gfg_plugin.engine_gate import gate  # noqa: E402


class EngineGateTest(unittest.TestCase):
    """User, 3.1.0: install the engine, reboot, only then the panel."""

    def test_fresh_plugin_asks_to_install(self):
        self.assertEqual(gate(None, "k-1", False, "b1", {})["state"], "install")

    def test_installed_in_this_boot_asks_to_reboot(self):
        self.assertEqual(gate("k-1", "k-1", True, "b1", {"boot_id": "b1", "version": "k-1"})["state"], "reboot")

    def test_after_reboot_the_panel_opens(self):
        self.assertEqual(gate("k-1", "k-1", True, "b2", {"boot_id": "b1", "version": "k-1"})["state"], "ready")

    def test_a_plugin_update_with_a_new_engine_asks_to_install_again(self):
        g = gate("k-1", "k-2", True, "b2", {"boot_id": "b1", "version": "k-1"})
        self.assertEqual((g["state"], g["update"]), ("install", True))

    def test_a_failed_install_keeps_the_panel_locked(self):
        g = gate(None, "k-1", False, "b1", {"error": "libfoo.so not found", "version": "k-1"})
        self.assertEqual(g["state"], "failed")
        self.assertIn("libfoo", g["error"])

    def test_rebooted_but_not_mounted_is_a_failure(self):
        self.assertEqual(gate("k-1", "k-1", False, "b2", {"boot_id": "b1", "version": "k-1"})["state"], "failed")

    def test_an_engine_installed_before_3_1_and_running_opens_the_panel(self):
        self.assertEqual(gate("k-1", "k-1", True, "b2", {})["state"], "ready")


if __name__ == "__main__":
    unittest.main()
