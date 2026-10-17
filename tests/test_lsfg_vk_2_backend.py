"""LSFG-VK 2.0 external FG ownership and environment contract."""
import logging
import os
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "py_modules"))
decky = types.ModuleType("decky")
decky.logger = logging.getLogger("lsfg-2-test")
decky.DECKY_USER_HOME = "/tmp/gfg-lsfg-test"
sys.modules.setdefault("decky", decky)

from gfg_plugin.config_schema import ConfigurationManager
from gfg_plugin.wrapper_generation import (script_configuration_lines, fg_backend_lines,
    layer_environment_lines, WrapperGenerationContext)
from gfg_plugin.dll_detection import DllDetectionService


class LSFGVk2BackendTests(unittest.TestCase):
    def test_select_and_persist_backend(self):
        cfg = ConfigurationManager.validate_config({"fg_backend": "LSFG_VK_2",
            "lsfg_vk_2_allow_fp16": False,
            "lsfg_vk_2_override_present_mode": False,
            "lsfg_vk_2_preserve_swapchain_image_count": True})
        self.assertEqual(cfg["fg_backend"], "lsfg_vk_2")
        self.assertFalse(cfg["lsfg_vk_2_allow_fp16"])
        self.assertTrue(cfg["lsfg_vk_2_preserve_swapchain_image_count"])

    def test_legacy_backend_migration_unchanged(self):
        self.assertEqual(ConfigurationManager.validate_config({"fg_backend": "lsfg"})["fg_backend"], "gfg")

    def test_external_owner_no_gfg_or_renderer(self):
        cfg = ConfigurationManager.validate_config({"fg_backend": "lsfg_vk_2",
            "scaling_enabled": True, "external_vulkan_layer": "vkbasalt"})
        effective = ConfigurationManager.get_effective_runtime_config(cfg)
        self.assertFalse(effective["frame_generation_enabled"])
        self.assertFalse(effective["frame_generation_provisioned"])
        self.assertFalse(effective["automatic_dock_mode"])
        self.assertIn("mako_renderer_required=0", script_configuration_lines(cfg))
        self.assertIn("export MAKO_FRAME_GENERATION_ENABLED=0", script_configuration_lines(cfg))

    def test_lsfg_environment_all_controls(self):
        cfg = ConfigurationManager.validate_config({"fg_backend":"lsfg_vk_2",
            "multiplier":3,"flow_scale":0.7,"performance_mode":True,
            "lsfg_vk_2_allow_fp16":False, "lsfg_vk_2_override_present_mode":False,
            "lsfg_vk_2_preserve_swapchain_image_count":True})
        lines = fg_backend_lines(cfg)
        script = "\n".join(lines) + """
printf 'VALUES:%s/%s/%s/%s/%s/%s/%s/%s/%s' "$LSFGVK_ENV" "$LSFGVK_MULTIPLIER" "$LSFGVK_FLOW_SCALE" "$LSFGVK_PERFORMANCE_MODE" "$LSFGVK_NO_FP16" "$LSFGVK_PACING_MODE" "$LSFGVK_OVERRIDE_PRESENT_MODE" "$LSFGVK_PRESERVE_SWAPCHAIN_IMAGE_COUNT" "$gfg_lsfg_vk_2_backend"
"""
        r = subprocess.run(["bash","-c",script],capture_output=True,text=True,check=True)
        self.assertIn("VALUES:1/3/0.7/1/1/vsync/0/1/1",r.stdout)

    def test_only_lsfg_backend_requests_lsfg_layer(self):
        for name in ("gfg","optiscaler","native","off"):
            cfg = ConfigurationManager.validate_config({"fg_backend":name})
            self.assertFalse(any("LSFGVK_ENV=1" in x for x in fg_backend_lines(cfg)))

    def test_installed_manifest_and_user_model(self):
        with tempfile.TemporaryDirectory(prefix="gfg-lsfg-dll-") as td:
            home = Path(td)
            model = home / "steamapps/common/Lossless Scaling/lsfg-vk.dll"
            model.parent.mkdir(parents=True)
            model.write_bytes(b"MZ placeholder for read-only presence")
            layer = home / ".local/share/vulkan/implicit_layer.d"
            layer.mkdir(parents=True)
            library = layer / "liblsfg.so"
            library.write_bytes(b"not executable (detector only)")
            manifest = layer / "VkLayer_LSFGVK_frame_generation.json"
            manifest.write_text('{"layer":{"name":"VK_LAYER_LSFGVK_frame_generation","implementation_version":2,"library_path":"./liblsfg.so"}}')
            with patch("gfg_plugin.base_service.resolve_user_home",return_value=home):
                d = DllDetectionService()
            with patch.object(d,"_get_steam_library_paths",return_value=[str(home)]):
                result = d.check_lsfg_vk_2()
            self.assertTrue(result["ready"])
            self.assertEqual(result["dll"],str(model))
            manifest.write_text('{"layer":{"name":"VK_LAYER_LSFGVK_frame_generation","implementation_version":1,"library_path":"./liblsfg.so"}}')
            self.assertFalse(d.check_lsfg_vk_2(str(model))["ready"])

    def test_legacy_lossless_dll_does_not_count_as_v2_model(self):
        with tempfile.TemporaryDirectory(prefix="gfg-lsfg-legacy-") as td:
            home=Path(td)
            p=home/"steamapps/common/Lossless Scaling/Lossless.dll"
            p.parent.mkdir(parents=True)
            p.write_bytes(b"MZ legacy")
            with patch("gfg_plugin.base_service.resolve_user_home",return_value=home):
                d=DllDetectionService()
            with patch.object(d,"_get_steam_library_paths",return_value=[str(home)]):
                result=d.check_lsfg_vk_2()
            self.assertFalse(result["ready"])
            self.assertIsNone(result["dll"])

    def test_selected_backend_only_activates_installed_implicit_layer(self):
        with tempfile.TemporaryDirectory(prefix="gfg-lsfg-wsi-") as td:
            home = Path(td)
            root = home / "tmp"
            ctx = WrapperGenerationContext(
                wrapper_format_marker="# x", host_compatibility_marker="# y",
                diagnostics_default_marker="# z", config_dir=root / "config",
                config_file_path=root / "conf.toml", runtime_state_dir=root / "runtime-state",
                local_share_dir=root / "share", renderer_bin_dir=root / "renderer",
                user_vulkan_layer_dir=root / "layers", spatial_scaling_layer_dir=root / "scaling",
                gamescope_wsi_compatibility_dir=root / "wsi", mangohud_layer_dir=root / "mango",
                vkbasalt_layer_dir=root / "vkbasalt", vkbasalt_global_config_path=root / "vkBasalt.conf",
                vkbasalt_profile_config_dir=root / "vkprofiles", flatpak_implicit_layer_dir="/tmp/flatpak",
                gamescope_wsi_manifest_filename_64="wsi.json", spatial_scaling_manifest_filename_64="spatial.json",
                mangohud_manifest_filename_64="mango.json", mangohud_manifest_filename_32="mango32.json",
                vkbasalt_manifest_filename_64="vkb.json", vkbasalt_manifest_filename_32="vkb32.json",
                armada_device_env=root / "device", armada_game_launch=root / "launcher",
            )
            lines = layer_environment_lines(ctx)
            start = next(i for i,line in enumerate(lines) if
                         line == 'if [ "${gfg_lsfg_vk_2_backend:-0}" = 1 ]; then')
            end = lines.index("unset gfg_lsfg_vk_2_backend", start)
            fragment = "\n".join(lines[start:end+1])
            probe = ('mako_implicit_layer_path=/tmp/gfg-layer\n'
                     'gfg_lsfg_vk_2_backend=1\n'
                     'export DISABLE_LSFGVK=1\n'
                     'export GFG_NATIVE_FG=1\n' + fragment + '\n'
                     'printf "RESULT:%s:%s:%s:%s\\n" '
                     '"${VK_INSTANCE_LAYERS:-}" "${VK_IMPLICIT_LAYER_PATH:-$mako_implicit_layer_path}" '
                     '"${DISABLE_LSFGVK:-unset}" "${GFG_NATIVE_FG:-unset}"\n')
            env = {"PATH":os.environ["PATH"], "HOME":str(home)}
            unavailable = subprocess.run(["bash","-c",probe],
                                         env=env,capture_output=True,text=True,check=True)
            self.assertIn("RESULT::/tmp/gfg-layer:1:unset", unavailable.stdout)
            manifest_dir = home / ".local/share/vulkan/implicit_layer.d"
            manifest_dir.mkdir(parents=True)
            (manifest_dir / "VkLayer_LSFGVK_frame_generation.json").write_text("{}")
            available = subprocess.run(["bash","-c",probe],
                                       env=env,capture_output=True,text=True,check=True)
            self.assertIn("VK_LAYER_LSFGVK_frame_generation",available.stdout)
            self.assertIn(str(manifest_dir),available.stdout)
            self.assertTrue(available.stdout.strip().endswith(":unset:unset"))

if __name__=="__main__":
    unittest.main()
