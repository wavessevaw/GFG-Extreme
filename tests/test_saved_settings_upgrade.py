"""Check preservation of saved settings without touching SteamOS or user files."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "py_modules"))
from gfg_plugin import settings


class SavedSettingsUpgradeTest(unittest.TestCase):
    def test_322_explicit_power_choices_survive_schema_upgrade(self):
        for split in (False, True):
            for gpu_clock in (False, True):
                with self.subTest(split=split, gpu_clock=gpu_clock):
                    saved = {"schema": 3, "power": {"enabled": True, "split": split,
                                                    "gpu_clock": gpu_clock}}
                    result = settings.normalize(saved)
                    self.assertEqual(result["power"], saved["power"])

    def test_later_settings_save_does_not_replace_322_power_choices(self):
        saved = {"schema": 3, "power": {"enabled": True, "split": True, "gpu_clock": True}}
        with patch.object(settings, "read_json", return_value=saved), \
             patch.object(settings, "write_json_atomic") as write:
            store = settings.Settings(Path("nonexistent-settings.json"))
            store.update_profile("default", {"fg": "off"})
        written = write.call_args.args[1]
        self.assertEqual(written["power"], saved["power"])
    def test_322_off_profile_remains_off(self):
        saved = {"schema": 3, "profiles": {"default": {"fg": "off"},
                                           "app:123": {"fg": "off"}}}
        profiles = settings.normalize(saved)["profiles"]
        self.assertEqual(profiles["default"]["fg"], "off")
        self.assertEqual(profiles["app:123"]["fg"], "off")

    def test_saved_fixed_modes_are_preserved_when_supported(self):
        for mode in ("auto", "x2", "x3", "x3.75", "custom"):
            with self.subTest(mode=mode):
                saved = {"schema": settings.SCHEMA, "profiles": {"default": {"fg": mode}}}
                self.assertEqual(settings.normalize(saved)["profiles"]["default"]["fg"], mode)


if __name__ == "__main__":
    unittest.main()
