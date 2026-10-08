"""1.3.1 regression: a game/profile switch must not force OLED 60 Hz.

Only a deliberate Target FPS change may own the global Gamescope refresh
slider. No Battery Playtime/Savings Effort policy is reintroduced.
"""
import asyncio
import logging
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "py_modules"))
if "decky" not in sys.modules:
    decky = types.ModuleType("decky")
    decky.logger = logging.getLogger("decky-refresh-test")
    decky.DECKY_USER_HOME = "/tmp/gfg-plugin-refresh-test"
    sys.modules["decky"] = decky

from gfg_plugin.plugin import Plugin  # noqa: E402


class ConfigStub:
    def __init__(self):
        self.config = {"target_fps": 60, "fg_backend": "gfg"}
        self.current = "oled"

    def set_current_profile(self, name):
        self.current = name
        return {"success": True, "profile_name": name}

    def sync_current_profile(self, app_id):
        self.current = "game-60"
        return {"success": True, "profile_name": self.current}

    def get_profile_config(self, name):
        return {"success": True, "config": dict(self.config)}

    def get_current_profile_snapshot(self):
        return self.current, {"config": dict(self.config)}

    def update_profile_config_fields(self, name, changes, origin, reason):
        self.config.update(changes)
        return {"success": True, "config": dict(self.config)}

    def update_profile_config(self, name, config, origin, reason):
        self.config.update(config)
        return {"success": True, "config": dict(self.config)}

    def update_config_from_dict(self, config, origin, reason):
        self.config.update(config)
        return {"success": True, "config": dict(self.config)}


class RefreshOwnershipTests(unittest.TestCase):
    def setUp(self):
        self.plugin = Plugin.__new__(Plugin)  # do not start Decky or Gamescope
        self.plugin.configuration_service = ConfigStub()
        self.plugin._schedule_refresh_from_config_response = Mock()
        async def safe(*args, **kwargs):
            return None
        self.plugin._restore_orphaned_dock_for_external_profile = safe

    def test_switching_profiles_cannot_force_saved_60_hz_on_oled(self):
        asyncio.run(self.plugin.set_current_profile("game-60"))
        asyncio.run(self.plugin.sync_current_profile("steam-game"))
        self.plugin._schedule_refresh_from_config_response.assert_not_called()

    def test_unrelated_field_edit_cannot_force_saved_60_hz(self):
        result = asyncio.run(self.plugin.update_profile_config_fields(
            "game-60", {"flow_scale": 0.5}))
        self.assertTrue(result["success"])
        self.plugin._schedule_refresh_from_config_response.assert_not_called()

    def test_explicit_target_fps_edit_still_syncs_gamescope(self):
        result = asyncio.run(self.plugin.update_profile_config_fields(
            "game-60", {"target_fps": 90}))
        self.assertTrue(result["success"])
        self.plugin._schedule_refresh_from_config_response.assert_called_once()
        response = self.plugin._schedule_refresh_from_config_response.call_args.args[0]
        self.assertEqual(response["config"]["target_fps"], 90)

    def test_full_config_write_with_unchanged_target_does_not_modeset(self):
        async def no_transition(*args, **kwargs):
            return None
        self.plugin._prepare_fg_backend_transition = no_transition
        result = asyncio.run(self.plugin.update_profile_config(
            "game-60", {"target_fps": 60, "flow_scale": 0.6}))
        self.assertTrue(result["success"])
        self.plugin._schedule_refresh_from_config_response.assert_not_called()

    def test_full_config_target_change_still_modesets(self):
        async def no_transition(*args, **kwargs):
            return None
        self.plugin._prepare_fg_backend_transition = no_transition
        result = asyncio.run(self.plugin.update_profile_config(
            "game-60", {"target_fps": 90, "flow_scale": 0.6}))
        self.assertTrue(result["success"])
        self.plugin._schedule_refresh_from_config_response.assert_called_once()


if __name__ == "__main__":
    unittest.main()
