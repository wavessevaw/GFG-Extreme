"""GFG Extreme backend ownership, OptiScaler wrapper, locking, and Dock tests."""
import asyncio
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import AsyncMock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "py_modules"))

TEMP_HOME = tempfile.mkdtemp(prefix="gfg-test-home-")
decky = types.ModuleType("decky")
decky.logger = logging.getLogger("decky-test")
decky.DECKY_USER_HOME = TEMP_HOME
sys.modules.setdefault("decky", decky)
HOME = sys.modules["decky"].DECKY_USER_HOME
logging.disable(logging.CRITICAL)

from gfg_plugin.config_schema import ConfigurationManager  # noqa: E402
from gfg_plugin.configuration import ConfigurationService  # noqa: E402
from gfg_plugin.plugin import Plugin  # noqa: E402
from gfg_plugin import wrapper_generation  # noqa: E402


def renderer_required(lines):
    for line in lines:
        if line.startswith("mako_renderer_required="):
            return line.rsplit("=", 1)[1] == "1"
    raise AssertionError("mako_renderer_required missing")


def run_backend_fragment(*, proxy="auto", files=(), existing=None, with_status=False):
    with tempfile.TemporaryDirectory(prefix="gfg-proxy-") as td:
        root = Path(td)
        for filename in files:
            (root / filename).touch()
        status_dir = root / "status" if with_status else None
        cfg = ConfigurationManager.validate_config({
            "fg_backend": "optiscaler",
            "optiscaler_proxy": proxy,
        })
        lines = wrapper_generation.fg_backend_lines(cfg, status_dir=status_dir)
        env = {"PATH": os.environ["PATH"]}
        if existing is not None:
            env["WINEDLLOVERRIDES"] = existing
        script = "\n".join(lines) + '\nprintf "RESULT=%s\\n" "${WINEDLLOVERRIDES-<unset>}"\n'
        completed = subprocess.run(
            ["bash", "-c", script], cwd=root, env=env,
            capture_output=True, text=True, check=True,
        )
        result = completed.stdout.strip().split("RESULT=", 1)[1]
        status = ""
        if status_dir is not None:
            path = status_dir / "gfg-extreme-optiscaler.status"
            if path.exists():
                status = path.read_text(encoding="utf-8")
        return result, status, script


class SchemaPolicy(unittest.TestCase):
    def test_01_default_backend_is_gfg(self):
        self.assertEqual(ConfigurationManager.validate_config({})["fg_backend"], "gfg")

    def test_02_legacy_lsfg_migrates_to_gfg(self):
        self.assertEqual(ConfigurationManager.validate_config({"fg_backend": "lsfg"})["fg_backend"], "gfg")

    def test_03_invalid_backend_rejected(self):
        with self.assertRaises(ValueError):
            ConfigurationManager.validate_config({"fg_backend": "afmf"})

    def test_04_backend_case_and_whitespace_normalised(self):
        cfg = ConfigurationManager.validate_config({"fg_backend": " OptiScaler "})
        self.assertEqual(cfg["fg_backend"], "optiscaler")

    def test_05_invalid_proxy_rejected(self):
        with self.assertRaises(ValueError):
            ConfigurationManager.validate_config({"optiscaler_proxy": "evil"})

    def test_06_default_proxy_is_auto(self):
        self.assertEqual(ConfigurationManager.validate_config({})["optiscaler_proxy"], "auto")

    def test_07_proxy_dll_suffix_is_normalised(self):
        cfg = ConfigurationManager.validate_config({"optiscaler_proxy": " DXGI.DLL "})
        self.assertEqual(cfg["optiscaler_proxy"], "dxgi")

    def test_08_validation_does_not_mutate_saved_fg_for_external_backend(self):
        cfg = ConfigurationManager.validate_config({
            "fg_backend": "optiscaler",
            "frame_generation_provisioned": True,
            "frame_generation_enabled": True,
            "automatic_dock_mode": True,
        })
        self.assertTrue(cfg["frame_generation_provisioned"])
        self.assertTrue(cfg["frame_generation_enabled"])
        self.assertTrue(cfg["automatic_dock_mode"])


class EffectiveRuntime(unittest.TestCase):
    def test_09_external_backend_effective_fg_false(self):
        cfg = ConfigurationManager.get_effective_runtime_config({
            "fg_backend": "optiscaler", "frame_generation_enabled": True,
        })
        self.assertFalse(cfg["frame_generation_enabled"])
        self.assertFalse(cfg["frame_generation_provisioned"])

    def test_10_external_backend_effective_dock_false(self):
        cfg = ConfigurationManager.get_effective_runtime_config({
            "fg_backend": "native", "automatic_dock_mode": True,
        })
        self.assertFalse(cfg["automatic_dock_mode"])

    def test_11_gfg_backend_restores_saved_effective_state(self):
        saved = ConfigurationManager.validate_config({
            "fg_backend": "gfg", "frame_generation_enabled": True,
            "frame_generation_provisioned": True, "automatic_dock_mode": True,
        })
        effective = ConfigurationManager.get_effective_runtime_config(saved)
        self.assertTrue(effective["frame_generation_enabled"])
        self.assertTrue(effective["frame_generation_provisioned"])
        self.assertTrue(effective["automatic_dock_mode"])

    def test_12_effective_projection_does_not_mutate_input(self):
        saved = ConfigurationManager.validate_config({
            "fg_backend": "off", "frame_generation_enabled": True,
            "automatic_dock_mode": True,
        })
        before = dict(saved)
        ConfigurationManager.get_effective_runtime_config(saved)
        self.assertEqual(saved, before)


class WrapperPolicy(unittest.TestCase):
    def lines(self, **over):
        return wrapper_generation.script_configuration_lines(
            ConfigurationManager.validate_config(over)
        )

    def test_13_gfg_fg_requires_renderer(self):
        self.assertTrue(renderer_required(self.lines(fg_backend="gfg")))

    def test_14_optiscaler_without_gfg_features_does_not_require_renderer(self):
        self.assertFalse(renderer_required(self.lines(
            fg_backend="optiscaler", scaling_enabled=False, external_vulkan_layer=""
        )))

    def test_15_optiscaler_with_scaling_requires_renderer(self):
        self.assertTrue(renderer_required(self.lines(
            fg_backend="optiscaler", scaling_enabled=True
        )))

    def test_16_native_with_shaders_requires_renderer(self):
        self.assertTrue(renderer_required(self.lines(
            fg_backend="native", external_vulkan_layer="vkbasalt"
        )))

    def test_17_off_everything_off_does_not_require_renderer(self):
        self.assertFalse(renderer_required(self.lines(
            fg_backend="off", scaling_enabled=False, external_vulkan_layer=""
        )))

    def test_18_external_backend_emits_runtime_fg_off_overrides(self):
        lines = self.lines(fg_backend="native")
        self.assertIn("export MAKO_FRAME_GENERATION_PROVISIONED=0", lines)
        self.assertIn("export MAKO_FRAME_GENERATION_ENABLED=0", lines)

    def test_19_gfg_backend_emits_no_forced_fg_off_override(self):
        lines = self.lines(fg_backend="gfg")
        self.assertNotIn("export MAKO_FRAME_GENERATION_PROVISIONED=0", lines)
        self.assertNotIn("export MAKO_FRAME_GENERATION_ENABLED=0", lines)

    def test_20_non_optiscaler_backend_has_no_proxy_logic(self):
        for backend in ("gfg", "native", "off"):
            cfg = ConfigurationManager.validate_config({"fg_backend": backend})
            self.assertEqual(wrapper_generation.fg_backend_lines(cfg), [], backend)


class OptiScalerWrapper(unittest.TestCase):
    def test_21_auto_detects_dxgi_first(self):
        result, status, _ = run_backend_fragment(
            files=("winmm.dll", "dxgi.dll", "d3d12.dll"), with_status=True
        )
        self.assertEqual(result, "dxgi=n,b")
        self.assertIn("detected=dxgi", status)

    def test_22_auto_detects_fallback_proxy(self):
        result, status, _ = run_backend_fragment(files=("winmm.dll",), with_status=True)
        self.assertEqual(result, "winmm=n,b")
        self.assertIn("detected=winmm", status)

    def test_23_explicit_proxy_is_respected(self):
        result, status, _ = run_backend_fragment(
            proxy="version", files=("dxgi.dll", "version.dll"), with_status=True
        )
        self.assertEqual(result, "version=n,b")
        self.assertIn("detected=version", status)

    def test_24_override_added_once(self):
        result, _, _ = run_backend_fragment(files=("dxgi.dll",))
        self.assertEqual(result.count("dxgi=n,b"), 1)

    def test_25_unrelated_existing_override_preserved(self):
        result, _, _ = run_backend_fragment(files=("dxgi.dll",), existing="foo=d")
        self.assertEqual(result, "foo=d;dxgi=n,b")

    def test_26_existing_same_dll_override_preserved(self):
        result, status, _ = run_backend_fragment(
            files=("dxgi.dll",), existing="dxgi=b", with_status=True
        )
        self.assertEqual(result, "dxgi=b")
        self.assertIn("status=external-override", status)
        self.assertIn("conflict=1", status)

    def test_27_missing_proxy_reports_not_found(self):
        result, status, _ = run_backend_fragment(with_status=True)
        self.assertEqual(result, "<unset>")
        self.assertIn("status=proxy-not-found", status)

    def test_28_generated_fragment_passes_bash_n(self):
        _, _, script = run_backend_fragment(files=("dxgi.dll",))
        subprocess.run(["bash", "-n"], input=script, text=True, check=True)


class ProfileRoundTrips(unittest.TestCase):
    def setUp(self):
        shutil.rmtree(HOME, ignore_errors=True)
        os.makedirs(HOME)
        self.svc = ConfigurationService()
        self.assertTrue(self.svc.create_profile("game", "mako")["success"])

    def cfg(self):
        return self.svc.get_profile_config("game")["config"]

    def configure_distinct_gfg_state(self):
        result = self.svc.update_profile_config_fields("game", {
            "frame_generation_provisioned": True,
            "frame_generation_enabled": False,
            "automatic_dock_mode": True,
            "adaptive": True,
            "target_fps": 73,
            "adaptive_max_multiplier": 4,
            "multiplier": 3,
            "scaling_enabled": True,
            "scaling_method": "mako",
            "external_vulkan_layer": "vkbasalt",
        })
        self.assertTrue(result["success"], result)
        return dict(self.cfg())

    def assert_round_trip(self, external):
        before = self.configure_distinct_gfg_state()
        self.assertTrue(self.svc.update_profile_config_fields(
            "game", {"fg_backend": external})["success"])
        middle = self.cfg()
        for key in (
            "frame_generation_provisioned", "frame_generation_enabled",
            "automatic_dock_mode", "adaptive", "target_fps",
            "adaptive_max_multiplier", "multiplier", "scaling_enabled",
            "scaling_method", "external_vulkan_layer",
        ):
            self.assertEqual(middle[key], before[key], (external, key))
        self.assertTrue(self.svc.update_profile_config_fields(
            "game", {"fg_backend": "gfg"})["success"])
        after = self.cfg()
        for key, value in before.items():
            if key not in {"fg_backend"}:
                self.assertEqual(after[key], value, key)

    def test_29_gfg_optiscaler_gfg_preserves_settings(self):
        self.assert_round_trip("optiscaler")

    def test_30_gfg_native_gfg_preserves_settings(self):
        self.assert_round_trip("native")

    def test_31_gfg_off_gfg_preserves_settings(self):
        self.assert_round_trip("off")

    def test_32_legacy_full_replace_preserves_backend_and_proxy(self):
        self.svc.update_profile_config_fields("game", {
            "fg_backend": "optiscaler", "optiscaler_proxy": "winmm"
        })
        legacy = dict(self.cfg())
        legacy.pop("fg_backend")
        legacy.pop("optiscaler_proxy")
        result = self.svc.update_profile_config("game", legacy)
        self.assertTrue(result["success"], result)
        self.assertEqual(self.cfg()["fg_backend"], "optiscaler")
        self.assertEqual(self.cfg()["optiscaler_proxy"], "winmm")

    def test_33_invalid_full_replace_returns_error_contract(self):
        result = self.svc.update_profile_config("game", {"fg_backend": "x"})
        self.assertFalse(result["success"])
        self.assertIsNone(result["config"])

    def test_34_concurrent_field_updates_have_no_lost_update(self):
        for _ in range(40):
            self.svc.update_profile_config_fields("game", {
                "target_fps": 90, "scaling_sharpness": 0.5
            })
            with ThreadPoolExecutor(max_workers=2) as pool:
                futures = [
                    pool.submit(self.svc.update_profile_config_fields, "game", {"target_fps": 61}),
                    pool.submit(self.svc.update_profile_config_fields, "game", {"scaling_sharpness": 0.73}),
                ]
                for future in futures:
                    self.assertTrue(future.result()["success"])
            cfg = self.cfg()
            self.assertEqual(cfg["target_fps"], 61)
            self.assertAlmostEqual(cfg["scaling_sharpness"], 0.73)

    def test_35_backend_update_and_sync_current_profile_do_not_lose_backend(self):
        self.svc.set_current_profile("game")
        with ThreadPoolExecutor(max_workers=2) as pool:
            a = pool.submit(self.svc.update_profile_config_fields, "game", {"fg_backend": "native"})
            b = pool.submit(self.svc.sync_current_profile, "")
            self.assertTrue(a.result()["success"])
            self.assertTrue(b.result()["success"])
        self.assertEqual(self.cfg()["fg_backend"], "native")

    def test_36_generated_multi_profile_wrapper_is_valid_bash(self):
        self.svc.update_profile_config_fields("game", {
            "fg_backend": "optiscaler", "optiscaler_proxy": "auto"
        })
        path = self.svc.mako_script_path
        subprocess.run(["bash", "-n", str(path)], check=True)
        text = path.read_text(encoding="utf-8")
        self.assertIn("MAKO_FRAME_GENERATION_ENABLED=0", text)
        self.assertIn("gfg_optiscaler_status", text)

    def test_41_plugin_legacy_profile_replace_preserves_backend_fields(self):
        self.svc.update_profile_config_fields("game", {
            "fg_backend": "optiscaler", "optiscaler_proxy": "winmm"
        })
        legacy = dict(self.cfg())
        legacy.pop("fg_backend")
        legacy.pop("optiscaler_proxy")
        plugin = Plugin()
        result = asyncio.run(plugin.update_profile_config("game", legacy))
        self.assertTrue(result["success"], result)
        self.assertEqual(self.cfg()["fg_backend"], "optiscaler")
        self.assertEqual(self.cfg()["optiscaler_proxy"], "winmm")

    def test_42_plugin_legacy_current_replace_preserves_backend_fields(self):
        self.svc.set_current_profile("game")
        self.svc.update_profile_config_fields("game", {
            "fg_backend": "native", "optiscaler_proxy": "version"
        })
        legacy = dict(self.cfg())
        legacy.pop("fg_backend")
        legacy.pop("optiscaler_proxy")
        plugin = Plugin()
        result = asyncio.run(plugin.update_mako_config(legacy))
        self.assertTrue(result["success"], result)
        self.assertEqual(self.cfg()["fg_backend"], "native")
        self.assertEqual(self.cfg()["optiscaler_proxy"], "version")


class DockPolicy(unittest.TestCase):
    def make_plugin(self, backend="gfg", dock=True):
        plugin = Plugin()
        cfg = ConfigurationManager.validate_config({
            "fg_backend": backend,
            "automatic_dock_mode": dock,
            "frame_generation_provisioned": True,
        })
        plugin.configuration_service.get_current_profile_snapshot = lambda: (
            "mako", {"success": True, "config": cfg}
        )
        return plugin

    def test_37_external_backend_skips_dock_state_and_gamescope(self):
        for backend in ("optiscaler", "native", "off"):
            plugin = self.make_plugin(backend)
            plugin._read_dock_state = lambda: (_ for _ in ()).throw(
                AssertionError("Dock state must not be read in external steady state")
            )
            plugin.gamescope_display_service.get_active_display_info = lambda: (_ for _ in ()).throw(
                AssertionError("Gamescope must not be queried")
            )
            asyncio.run(plugin._automatic_dock_iteration())

    def test_38_gfg_backend_still_queries_gamescope(self):
        plugin = self.make_plugin("gfg")
        plugin._read_dock_state = lambda: None
        called = {"count": 0}
        def display():
            called["count"] += 1
            return {"success": False}
        plugin.gamescope_display_service.get_active_display_info = display
        asyncio.run(plugin._automatic_dock_iteration())
        self.assertEqual(called["count"], 1)

    def test_39_backend_switch_restores_snapshot_before_external_ownership(self):
        plugin = self.make_plugin("gfg")
        state = {"schema": 1, "profile": "mako", "original": {"target_fps": 90}}
        reads = iter((state, None))
        plugin._read_dock_state = lambda: next(reads)
        plugin._restore_dock_profile = AsyncMock()
        original = asyncio.run(plugin._prepare_fg_backend_transition("mako", "native"))
        plugin._restore_dock_profile.assert_awaited_once_with(state)
        self.assertEqual(original, {"target_fps": 90})

    def test_40_forced_unload_does_not_restore_after_monitor_timeout(self):
        async def scenario():
            plugin = Plugin()
            plugin._display_sync_task = None
            plugin._dock_monitor_task = asyncio.create_task(asyncio.sleep(3600))
            plugin._read_dock_state = lambda: {"saved": {"target_fps": 90}}
            plugin._restore_dock_profile = AsyncMock()
            original_wait_for = asyncio.wait_for
            async def fake_wait_for(awaitable, timeout):
                if timeout == 15.0:
                    raise asyncio.TimeoutError
                return await original_wait_for(awaitable, timeout)
            with patch("gfg_plugin.plugin.asyncio.wait_for", side_effect=fake_wait_for):
                await plugin._unload()
            plugin._restore_dock_profile.assert_not_awaited()
        asyncio.run(scenario())


if __name__ == "__main__":
    unittest.main(verbosity=2)
