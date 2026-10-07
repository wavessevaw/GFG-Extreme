"""`mako-run` was renamed to `gfg`; the old command must keep working as an alias."""
import logging
import shlex
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
TEMP_HOME = tempfile.mkdtemp(prefix="gfg-rename-home-")
decky = types.ModuleType("decky")
decky.logger = logging.getLogger("decky-test")
decky.DECKY_USER_HOME = TEMP_HOME
sys.modules.setdefault("decky", decky)
HOME = sys.modules["decky"].DECKY_USER_HOME

from shared_config import MAKO_WRAPPER_RELATIVE_PATH  # noqa: E402
from gfg_plugin.configuration import ConfigurationService  # noqa: E402


class LauncherRenameTests(unittest.TestCase):
    def setUp(self):
        shutil.rmtree(HOME, ignore_errors=True)
        os.makedirs(Path(HOME) / ".local/bin")
        self.legacy = Path(HOME) / ".local/bin/mako-run"
        self.svc = ConfigurationService()

    def test_new_command_is_gfg(self):
        self.assertEqual(MAKO_WRAPPER_RELATIVE_PATH, ".local/bin/gfg")
        self.assertEqual(self.svc.mako_script_path, Path(HOME) / ".local/bin/gfg")

    def test_fresh_install_does_not_create_legacy_alias(self):
        self.svc.update_mako_script(self.svc._get_profile_data()["profiles"]["mako"])
        self.assertTrue(self.svc.mako_script_path.is_file())
        self.assertFalse(self.legacy.exists())

    def test_old_generated_wrapper_becomes_alias_of_new_launcher(self):
        self.legacy.write_text("#!/bin/bash\n# mako-wrapper-format: 74\nold\n")
        self.svc.update_mako_script(self.svc._get_profile_data()["profiles"]["mako"])
        text = self.legacy.read_text()
        self.assertIn("gfg-legacy-launcher", text)
        self.assertIn(f'exec {shlex.quote(str(self.svc.mako_script_path))} "$@"', text)
        self.assertTrue(os.access(self.legacy, os.X_OK))

    def test_user_owned_file_is_never_overwritten(self):
        self.legacy.write_text("#!/bin/sh\necho mine\n")
        self.svc.update_mako_script(self.svc._get_profile_data()["profiles"]["mako"])
        self.assertEqual(self.legacy.read_text(), "#!/bin/sh\necho mine\n")

    def test_alias_runs_the_new_launcher(self):
        self.legacy.write_text("# mako-wrapper-format: 1\n")
        self.svc.update_mako_script(self.svc._get_profile_data()["profiles"]["mako"])
        import subprocess
        done = subprocess.run(
            [str(self.legacy), "/usr/bin/env"], capture_output=True, text=True, timeout=30,
            env={"PATH": os.environ["PATH"], "HOME": HOME},
        )
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("MAKO_CONFIG=", done.stdout)


if __name__ == "__main__":
    unittest.main()
