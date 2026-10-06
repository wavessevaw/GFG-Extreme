"""OptiScaler proxy discovery: where the proxy really lives, and status plumbing."""
import asyncio
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

_TEMP_HOME = tempfile.mkdtemp(prefix="gfg-disc-home-")
_decky = types.ModuleType("decky")
_decky.logger = logging.getLogger("decky-test")
_decky.DECKY_USER_HOME = _TEMP_HOME
sys.modules.setdefault("decky", _decky)
logging.disable(logging.CRITICAL)
HOME = sys.modules["decky"].DECKY_USER_HOME  # whichever test module won setdefault

from gfg_plugin.config_schema import ConfigurationManager  # noqa: E402
from gfg_plugin.configuration import ConfigurationService  # noqa: E402
from gfg_plugin.plugin import Plugin  # noqa: E402
from gfg_plugin import wrapper_generation  # noqa: E402


def probe(proxy="auto", cwd=None, args=(), env=None, status_dir=None):
    """Run only the generated OptiScaler block and return (overrides, status)."""
    cfg = ConfigurationManager.validate_config(
        {"fg_backend": "optiscaler", "optiscaler_proxy": proxy})
    lines = wrapper_generation.fg_backend_lines(cfg, status_dir=status_dir)
    script = "\n".join(lines) + '\nprintf "RESULT=%s\\n" "${WINEDLLOVERRIDES-<unset>}"\nprintf "STATUS=%s\\n" "$gfg_optiscaler_status"\nprintf "WAY=%s\\n" "$gfg_optiscaler_how"\n'
    full_env = {"PATH": os.environ["PATH"], **(env or {})}
    out = subprocess.run(["bash", "-c", script, "_", *args], cwd=cwd, env=full_env,
                         capture_output=True, text=True, check=True).stdout
    values = dict(line.split("=", 1) for line in out.strip().splitlines())
    return values["RESULT"], values["STATUS"], values["WAY"]


class Layout(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="gfg-game-"))
        self.install = self.tmp / "My Game [x]"
        self.exe_dir = self.install / "Binaries" / "Win64"
        self.exe_dir.mkdir(parents=True)
        (self.exe_dir / "Game.exe").touch()
        self.exe = str(self.exe_dir / "Game.exe")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def install_proxy(self, name="dxgi.dll", ini=True):
        (self.exe_dir / name).touch()
        if ini:
            (self.exe_dir / "OptiScaler.ini").touch()


class Discovery(Layout):
    def test_proxy_beside_exe_found_from_install_root_cwd(self):
        # The reported failure: Steam's cwd is the install root, the proxy is beside the exe.
        self.install_proxy()
        self.assertEqual(probe(cwd=self.install, args=(self.exe, "-dx12")),
                         ("dxgi=n,b", "ready", "ini"))

    def test_steam_install_path_search_without_exe_argument(self):
        self.install_proxy()
        self.assertEqual(
            probe(cwd=self.install, env={"STEAM_COMPAT_INSTALL_PATH": str(self.install)}),
            ("dxgi=n,b", "ready", "search"))

    def test_case_insensitive_names(self):
        self.install_proxy("DXGI.DLL")
        self.assertEqual(probe(cwd=self.install, args=(self.exe,))[:2], ("dxgi=n,b", "ready"))

    def test_other_proxy_name_with_marker(self):
        self.install_proxy("winmm.dll")
        self.assertEqual(probe(cwd=self.install, args=(self.exe,))[:2], ("winmm=n,b", "ready"))

    def test_name_only_fallback_without_ini(self):
        self.install_proxy("dxgi.dll", ini=False)
        self.assertEqual(probe(cwd=self.install, args=(self.exe,)),
                         ("dxgi=n,b", "unverified", "name"))

    def test_legacy_cwd_detection_still_works(self):
        (self.exe_dir / "dxgi.dll").touch()
        self.assertEqual(probe(cwd=self.exe_dir)[:2], ("dxgi=n,b", "unverified"))

    def test_nothing_installed_leaves_overrides_alone(self):
        self.assertEqual(probe(cwd=self.install, args=(self.exe,)),
                         ("<unset>", "proxy-not-found", ""))

    def test_existing_same_proxy_override_wins(self):
        self.install_proxy()
        self.assertEqual(
            probe(cwd=self.install, args=(self.exe,), env={"WINEDLLOVERRIDES": "dxgi=b"})[:2],
            ("dxgi=b", "external-override"))

    def test_existing_same_proxy_override_is_case_insensitive(self):
        self.install_proxy()
        self.assertEqual(
            probe(cwd=self.install, args=(self.exe,), env={"WINEDLLOVERRIDES": "DXGI=b"})[:2],
            ("DXGI=b", "external-override"))

    def test_unrelated_override_is_merged_not_replaced(self):
        self.install_proxy()
        self.assertEqual(
            probe(cwd=self.install, args=(self.exe,), env={"WINEDLLOVERRIDES": "foo=d"})[0],
            "foo=d;dxgi=n,b")

    def test_manual_proxy_applies_even_when_file_not_verified(self):
        result, status, _ = probe("version", cwd=self.install, args=(self.exe,))
        self.assertEqual((result, status), ("version=n,b", "proxy-not-found"))

    def test_manual_proxy_verified_beside_exe(self):
        self.install_proxy("Version.DLL")
        self.assertEqual(probe("version", cwd=self.install, args=(self.exe,))[:2],
                         ("version=n,b", "ready"))

    def test_launch_arguments_are_untouched(self):
        cfg = ConfigurationManager.validate_config({"fg_backend": "optiscaler"})
        script = "\n".join(wrapper_generation.fg_backend_lines(cfg)) + \
            '\nprintf "%s|" "$#" "$@"\n'
        out = subprocess.run(["bash", "-c", script, "_", self.exe, "a b", "*", "-x"],
                             cwd=self.install, capture_output=True, text=True,
                             check=True, env={"PATH": os.environ["PATH"]}).stdout
        self.assertEqual(out, f"4|{self.exe}|a b|*|-x|")


class ServicePath(Layout):
    """The real generation path (ConfigurationService) must publish discovery status."""

    def setUp(self):
        super().setUp()
        shutil.rmtree(HOME, ignore_errors=True)
        os.makedirs(HOME)
        self.svc = ConfigurationService()
        self.assertTrue(self.svc.create_profile("ue", "mako")["success"])
        self.assertTrue(self.svc.update_profile_config_fields(
            "ue", {"fg_backend": "optiscaler"})["success"])

    def test_generated_wrapper_contains_status_writer_and_is_valid_bash(self):
        wrapper = Path(self.svc.mako_script_path)
        text = wrapper.read_text(encoding="utf-8")
        self.assertIn("gfg_optiscaler_status_path", text)
        subprocess.run(["bash", "-n", str(wrapper)], check=True)

    def test_status_round_trip_reaches_the_plugin_api(self):
        self.install_proxy()
        env = {"PATH": os.environ["PATH"], "HOME": HOME, "MAKO_PROFILE": "ue"}
        subprocess.run([str(self.svc.mako_script_path), "true", "_", self.exe],
                       cwd=self.install, env=env, check=True)
        status = asyncio.run(Plugin().get_fg_backend_status("ue"))
        self.assertEqual(status["optiscaler_status"], "ready")
        self.assertEqual(status["optiscaler_proxy_detected"], "dxgi")
        self.assertEqual(status["optiscaler_dir"], str(self.exe_dir))
        self.assertEqual(status["optiscaler_detection"], "ini")
        self.assertEqual(status["optiscaler_override"], "dxgi=n,b")

    def test_name_only_status_round_trip_is_unverified(self):
        self.install_proxy(ini=False)
        env = {"PATH": os.environ["PATH"], "HOME": HOME, "MAKO_PROFILE": "ue"}
        subprocess.run([str(self.svc.mako_script_path), "true", "_", self.exe],
                       cwd=self.install, env=env, check=True)
        status = asyncio.run(Plugin().get_fg_backend_status("ue"))
        self.assertEqual(status["optiscaler_status"], "unverified")
        self.assertEqual(status["optiscaler_proxy_detected"], "dxgi")
        self.assertEqual(status["optiscaler_detection"], "name")


if __name__ == "__main__":
    unittest.main()
