"""1.0.9: reinstalling the engine must never silently drop the user's profiles."""
import logging
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
decky.DECKY_USER_HOME = tempfile.mkdtemp(prefix="gfg-install-home-")
sys.modules.setdefault("decky", decky)

from gfg_plugin.installation import InstallationService  # noqa: E402


class ConfigBackupTests(unittest.TestCase):
    def test_unmergeable_config_is_kept_as_a_backup(self):
        with tempfile.TemporaryDirectory() as temp:
            ins = InstallationService()
            ins.config_file_path = Path(temp) / "conf.toml"
            from gfg_plugin.configuration import ConfigurationService
            cs = ConfigurationService()
            cs.config_file_path = ins.config_file_path
            cs.get_profiles(); cs.create_profile("Elden")
            text = ins.config_file_path.read_text()
            i = text.rfind("pacing = ")
            original = text[:i] + "pacing = 'from-a-newer-build'\n"   # a value this build rejects
            ins.config_file_path.write_text(original)
            ins._create_config_file()
            backups = list(Path(temp).glob("conf.toml.bak-*"))
            self.assertEqual(len(backups), 1)
            self.assertEqual(backups[0].read_text(), original)
            self.assertIn("[[profile]]", ins.config_file_path.read_text())


class SettingsSidecarTests(unittest.TestCase):
    def test_damaged_wrapper_settings_are_kept_aside(self):
        from gfg_plugin.profile_storage import read_wrapper_profile_settings
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "wrapper-profiles.json"
            path.write_text('{"profiles": {"other": {"fg_backend": "optis')        # torn
            self.assertEqual(read_wrapper_profile_settings(path, 1, logging.getLogger("t")), {})
            self.assertTrue((Path(temp) / "wrapper-profiles.json.damaged").is_file())


if __name__ == "__main__":
    unittest.main()
