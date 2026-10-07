"""1.0.9: renaming or deleting a profile while Automatic Dock holds its handheld snapshot."""
import asyncio
import logging
import os
import shutil
import sys
import tempfile
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "py_modules"))
decky = types.ModuleType("decky")
decky.logger = logging.getLogger("decky-test")
decky.DECKY_USER_HOME = tempfile.mkdtemp(prefix="gfg-dock-home-")
sys.modules.setdefault("decky", decky)
HOME = sys.modules["decky"].DECKY_USER_HOME

from gfg_plugin.plugin import Plugin  # noqa: E402

DOCKED = {"success": True, "external": True, "connector": "HDMI-A-1", "valid_rates": [60]}
HANDHELD = {"success": True, "external": False, "internal": True, "valid_rates": [90]}


class DockLifecycleTests(unittest.TestCase):
    def setUp(self):
        shutil.rmtree(HOME, ignore_errors=True)
        os.makedirs(HOME)
        self.plugin = Plugin()
        cs = self.cs = self.plugin.configuration_service
        cs.create_profile("game"); cs.set_current_profile("game")
        cs.update_profile_config_fields("game", {"automatic_dock_mode": True, "target_fps": 90, "multiplier": 2,
                                                 "adaptive": False}, "user")
        gd = self.gd = self.plugin.gamescope_display_service
        gd.sync_target_fps = lambda t: {"success": True, "applied": True, "verified": True, "verified_refresh_hz": t}
        gd.read_current_refresh_hz = lambda: 60
        gd.get_active_display_info = lambda: DOCKED
        asyncio.run(self.plugin._automatic_dock_iteration())
        self.assertEqual(self.plugin._read_dock_state()["profile"], "game")

    def test_rename_while_docked_keeps_the_handheld_values(self):
        self.assertTrue(asyncio.run(self.plugin.rename_profile("game", "handheld"))["success"])
        self.assertEqual(self.plugin._read_dock_state()["profile"], "handheld")
        asyncio.run(self.plugin._automatic_dock_iteration())
        self.gd.get_active_display_info = lambda: HANDHELD
        asyncio.run(self.plugin._automatic_dock_iteration())
        config = self.cs.get_profile_config("handheld")["config"]
        self.assertEqual((config["target_fps"], config["multiplier"]), (90, 2))
        self.assertIsNone(self.plugin._read_dock_state())

    def test_deleting_the_docked_profile_releases_dock(self):
        self.cs.create_profile("other"); self.cs.set_current_profile("other")
        self.assertTrue(asyncio.run(self.plugin.delete_profile("game"))["success"])
        self.assertIsNone(self.plugin._read_dock_state())

    def test_a_snapshot_whose_profile_vanished_is_dropped(self):
        self.cs.create_profile("other"); self.cs.set_current_profile("other")
        self.cs.delete_profile("game")                  # bypassing the plugin RPC
        self.gd.get_active_display_info = lambda: HANDHELD
        asyncio.run(self.plugin._automatic_dock_iteration())
        self.assertIsNone(self.plugin._read_dock_state())


if __name__ == "__main__":
    unittest.main()
