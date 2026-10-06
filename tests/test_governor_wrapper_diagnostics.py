import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "py_modules"))

from gfg_plugin.wrapper_generation import WrapperGenerationContext, layer_environment_lines, WRAPPER_FORMAT_VERSION


class GovernorWrapperDiagnosticsTests(unittest.TestCase):
    def test_wrapper_format_bumped_for_governor_diagnostics(self):
        self.assertGreaterEqual(WRAPPER_FORMAT_VERSION, 75)

    def test_layer_environment_uses_governor_marker(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            ctx = WrapperGenerationContext(
                wrapper_format_marker="# x", host_compatibility_marker="# y",
                diagnostics_default_marker="# z", config_dir=root / "config",
                config_file_path=root / "config/conf.toml", runtime_state_dir=root / "runtime-state",
                local_share_dir=root / "share", renderer_bin_dir=root / "renderer",
                user_vulkan_layer_dir=root / "layers", spatial_scaling_layer_dir=root / "scaling",
                gamescope_wsi_compatibility_dir=root / "wsi", mangohud_layer_dir=root / "mango",
                vkbasalt_layer_dir=root / "vkbasalt", vkbasalt_global_config_path=root / "vkBasalt.conf",
                vkbasalt_profile_config_dir=root / "vkprofiles", flatpak_implicit_layer_dir="/tmp/flatpak",
                gamescope_wsi_manifest_filename_64="wsi.json", spatial_scaling_manifest_filename_64="scaling.json",
                mangohud_manifest_filename_64="mango64.json", mangohud_manifest_filename_32="mango32.json",
                vkbasalt_manifest_filename_64="vkb64.json", vkbasalt_manifest_filename_32="vkb32.json",
                armada_device_env=root / "device", armada_game_launch=root / "launch",
            )
            text = "\n".join(layer_environment_lines(ctx))
            self.assertIn("governor-diagnostics.enabled", text)
            self.assertIn("MAKO_PRESENT_DIAGNOSTICS", text)
            self.assertIn(":-1", text)
            self.assertIn(":-0", text)


if __name__ == "__main__":
    unittest.main()
