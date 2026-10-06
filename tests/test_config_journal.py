"""Configuration journal recording and schema-safe restore."""
import asyncio
import logging
import os
import shutil
import sys
import tempfile
import types
import unittest
from unittest.mock import AsyncMock
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "py_modules"))
TEMP_HOME = tempfile.mkdtemp(prefix="gfg-journal-home-")
decky = types.ModuleType("decky")
decky.logger = logging.getLogger("decky-test")
decky.DECKY_USER_HOME = TEMP_HOME
sys.modules.setdefault("decky", decky)
HOME = sys.modules["decky"].DECKY_USER_HOME

from gfg_plugin.configuration import ConfigurationService  # noqa: E402
from gfg_plugin.plugin import Plugin  # noqa: E402


class ConfigJournalTests(unittest.TestCase):
    def setUp(self):
        shutil.rmtree(HOME, ignore_errors=True)
        os.makedirs(HOME)
        self.svc = ConfigurationService()
        self.assertTrue(self.svc.create_profile("game", "mako")["success"])

    def test_update_records_actor_reason_and_diff(self):
        before = self.svc.get_profile_config("game")["config"]["target_fps"]
        result = self.svc.update_profile_config_fields(
            "game", {"target_fps": before + 7}, "ui", "test change"
        )
        self.assertTrue(result["success"], result)
        entries = self.svc.get_config_journal("game", 10)["entries"]
        self.assertTrue(entries)
        entry = entries[0]
        self.assertEqual(entry["actor"], "ui")
        self.assertEqual(entry["reason"], "test change")
        self.assertEqual(entry["changes"]["target_fps"]["before"], before)
        self.assertEqual(entry["changes"]["target_fps"]["after"], before + 7)

    def test_restore_reverts_only_recorded_fields_and_creates_recovery_entry(self):
        original = self.svc.get_profile_config("game")["config"]["target_fps"]
        self.svc.update_profile_config_fields(
            "game", {"target_fps": original + 11}, "ui", "raise target"
        )
        entry = self.svc.get_config_journal("game", 1)["entries"][0]
        result = self.svc.restore_config_journal_entry(entry["id"])
        self.assertTrue(result["success"], result)
        self.assertEqual(self.svc.get_profile_config("game")["config"]["target_fps"], original)
        latest = self.svc.get_config_journal("game", 1)["entries"][0]
        self.assertEqual(latest["actor"], "recovery")

    def test_plugin_restore_backend_prepares_transition_before_write(self):
        self.svc.update_profile_config_fields(
            "game", {"fg_backend": "native"}, "backend", "external owner"
        )
        entry = self.svc.get_config_journal("game", 1)["entries"][0]

        plugin = Plugin()
        plugin.configuration_service = self.svc
        plugin.pipeline_inspector_service.configuration_service = self.svc
        plugin._prepare_fg_backend_transition = AsyncMock(return_value=None)
        plugin._schedule_refresh_from_config_response = lambda *args, **kwargs: None

        result = asyncio.run(plugin.restore_config_journal_entry(entry["id"]))
        self.assertTrue(result["success"], result)
        plugin._prepare_fg_backend_transition.assert_awaited_once_with("game", "gfg")
        self.assertEqual(
            self.svc.get_profile_config("game")["config"]["fg_backend"], "gfg"
        )


if __name__ == "__main__":
    unittest.main()
