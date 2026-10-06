"""The generated launch wrapper selects the Governor overlay only under a live lease."""
import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "py_modules"))
TEMP_HOME = tempfile.mkdtemp(prefix="gfg-wrapov-home-")
decky = types.ModuleType("decky")
decky.logger = logging.getLogger("decky-test")
decky.DECKY_USER_HOME = TEMP_HOME
sys.modules.setdefault("decky", decky)
HOME = sys.modules["decky"].DECKY_USER_HOME

from gfg_plugin.configuration import ConfigurationService  # noqa: E402
from gfg_plugin.governor_overlay import OverlayStore  # noqa: E402
from gfg_plugin.pipeline_inspector import profile_manifest_key  # noqa: E402


class WrapperOverlayTests(unittest.TestCase):
    def setUp(self):
        shutil.rmtree(HOME, ignore_errors=True)
        os.makedirs(HOME)
        self.svc = ConfigurationService()
        self.assertTrue(self.svc.create_profile("game", "mako")["success"])
        self.assertTrue(self.svc.set_current_profile("game")["success"])
        self.script = self.svc.mako_script_path
        self.assertTrue(self.script.is_file())

    def store(self, pid):
        return OverlayStore(self.svc.config_dir, self.svc.build_governor_overlay_text, owner_pid=pid)

    def run_wrapper(self):
        env = {"PATH": os.environ["PATH"], "HOME": HOME, "MAKO_PROFILE": "game"}
        done = subprocess.run(
            ["bash", str(self.script), "/usr/bin/env"],
            env=env, capture_output=True, text=True, timeout=30,
        )
        self.assertEqual(done.returncode, 0, done.stderr)
        values = dict(line.split("=", 1) for line in done.stdout.splitlines() if "=" in line)
        manifest = self.svc.runtime_state_dir / "launches" / f"{profile_manifest_key('game')}.json"
        data = json.loads(manifest.read_text()) if manifest.exists() else {}
        return values.get("MAKO_CONFIG"), data

    def test_script_declares_overlay_and_format_76(self):
        text = self.script.read_text()
        self.assertIn("# mako-wrapper-format: 76", text)
        self.assertIn("mako_governor_overlay=", text)
        self.assertIn("mako_governor_overlay_active=", text)

    def test_no_overlay_uses_saved_config(self):
        config, manifest = self.run_wrapper()
        self.assertEqual(config, str(self.svc.config_file_path))
        self.assertEqual(manifest.get("governor_launch"), "")

    def test_live_owner_selects_overlay_and_manifest_records_launch_capability(self):
        rec = self.store(os.getpid()).write("game", {}, point_key="base")
        config, manifest = self.run_wrapper()
        self.assertEqual(config, rec.path)
        self.assertEqual(manifest["governor_launch"], f"scaling=0 rev={rec.revision} owner={os.getpid()}")

    def test_dead_owner_falls_back_to_saved(self):
        self.store(2 ** 22 + 12345).write("game", {}, point_key="45x2")
        config, manifest = self.run_wrapper()
        self.assertEqual(config, str(self.svc.config_file_path))
        self.assertEqual(manifest["governor_launch"], "")

    def test_released_overlay_is_ignored_for_new_launches(self):
        self.store(os.getpid()).write("game", {}, point_key="released", released=True)
        config, _ = self.run_wrapper()
        self.assertEqual(config, str(self.svc.config_file_path))

    def test_garbage_header_is_ignored(self):
        path = self.store(os.getpid()).write("game", {}).path
        Path(path).write_text("# gfg-governor-launch: owner=;rm -rf /\n" + Path(path).read_text())
        config, _ = self.run_wrapper()
        self.assertEqual(config, str(self.svc.config_file_path))
        self.assertTrue(Path(path).exists())

    def test_overlay_for_other_profile_is_not_used(self):
        self.assertTrue(self.svc.create_profile("other", "mako")["success"])
        self.store(os.getpid()).write("other", {}, point_key="base")
        config, _ = self.run_wrapper()
        self.assertEqual(config, str(self.svc.config_file_path))


if __name__ == "__main__":
    unittest.main()
