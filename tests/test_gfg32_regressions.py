"""Regression coverage for the gfg.3.2 baseline fixes."""
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
TEMP_HOME = tempfile.mkdtemp(prefix="gfg32-home-")
decky = types.ModuleType("decky")
decky.logger = logging.getLogger("decky-test")
decky.DECKY_USER_HOME = TEMP_HOME
sys.modules.setdefault("decky", decky)
HOME = sys.modules["decky"].DECKY_USER_HOME

from gfg_plugin.config_schema import ConfigurationManager  # noqa: E402
from gfg_plugin.configuration import ConfigurationService  # noqa: E402
from gfg_plugin.plugin import Plugin  # noqa: E402
from gfg_plugin import wrapper_generation  # noqa: E402


def run_fragment(proxy="auto", existing="", cwd=None):
    cfg = ConfigurationManager.validate_config({"fg_backend": "optiscaler", "optiscaler_proxy": proxy})
    script = "\n".join(wrapper_generation.fg_backend_lines(cfg)) + \
        '\nprintf "RESULT=%s\\nSTATUS=%s\\n" "${WINEDLLOVERRIDES-<unset>}" "$gfg_optiscaler_status"\n'
    env = {"PATH": os.environ["PATH"]}
    if existing:
        env["WINEDLLOVERRIDES"] = existing
    out = __import__("subprocess").run(
        ["bash", "-c", script], cwd=cwd, env=env, capture_output=True, text=True, check=True
    ).stdout
    return dict(line.split("=", 1) for line in out.strip().splitlines())


class Gfg32Regression(unittest.TestCase):
    def setUp(self):
        shutil.rmtree(HOME, ignore_errors=True)
        os.makedirs(HOME)

    def test_grouped_override_conflict_is_detected(self):
        tmp = Path(tempfile.mkdtemp(prefix="gfg32-proxy-"))
        try:
            (tmp / "dxgi.dll").touch()
            result = run_fragment(existing="D3D11,DXGI=b", cwd=tmp)
            self.assertEqual(result["RESULT"], "D3D11,DXGI=b")
            self.assertEqual(result["STATUS"], "external-override")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_explicit_proxy_file_without_ini_is_ready(self):
        tmp = Path(tempfile.mkdtemp(prefix="gfg32-proxy-"))
        try:
            (tmp / "Version.DLL").touch()
            result = run_fragment(proxy="version", cwd=tmp)
            self.assertEqual(result["RESULT"], "version=n,b")
            self.assertEqual(result["STATUS"], "ready")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_selecting_external_profile_restores_orphaned_dock_snapshot(self):
        svc = ConfigurationService()
        self.assertTrue(svc.create_profile("external", "mako")["success"])
        self.assertTrue(svc.update_profile_config_fields(
            "external", {"fg_backend": "native"}
        )["success"])
        plugin = Plugin()
        restored = []
        plugin._write_dock_state({
            "schema": 1,
            "profile": "mako",
            "original": {"target_fps": 60},
            "target_fps": 60,
        })

        async def fake_restore(state):
            restored.append(state["profile"])
            plugin._clear_dock_state()

        plugin._restore_dock_profile = fake_restore
        result = asyncio.run(plugin.set_current_profile("external"))
        self.assertTrue(result["success"], result)
        self.assertEqual(restored, ["mako"])
        self.assertIsNone(plugin._read_dock_state())


if __name__ == "__main__":
    unittest.main()
