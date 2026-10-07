import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "py_modules"))

from gfg_plugin.wrapper_generation import (  # noqa: E402
    FRAME_OS_LAYER_NAME, FRAME_OS_MANIFEST_FILENAME, WrapperGenerationContext, layer_environment_lines,
)


class FrameOsLaunchOrderTests(unittest.TestCase):
    """The pacer is named first in VK_INSTANCE_LAYERS (above the renderer) and never joins implicitly."""

    def setUp(self):
        self._temp = tempfile.TemporaryDirectory()
        self.root = Path(self._temp.name)
        self.layer_dir = self.root / "frame-os-layer"
        self.marker = self.root / "runtime-state" / "frame-os.enabled"
        self.ctx = WrapperGenerationContext(
            wrapper_format_marker="# x", host_compatibility_marker="# y",
            diagnostics_default_marker="# z", config_dir=self.root / "config",
            config_file_path=self.root / "config/conf.toml", runtime_state_dir=self.root / "runtime-state",
            local_share_dir=self.root / "share", renderer_bin_dir=self.root / "renderer",
            user_vulkan_layer_dir=self.root / "layers", spatial_scaling_layer_dir=self.root / "scaling",
            gamescope_wsi_compatibility_dir=self.root / "wsi", mangohud_layer_dir=self.root / "mango",
            vkbasalt_layer_dir=self.root / "vkbasalt", vkbasalt_global_config_path=self.root / "vkBasalt.conf",
            vkbasalt_profile_config_dir=self.root / "vkprofiles",
            flatpak_implicit_layer_dir=str(self.root / "no-flatpak"),
            gamescope_wsi_manifest_filename_64="wsi.json", spatial_scaling_manifest_filename_64="scaling.json",
            mangohud_manifest_filename_64="mango64.json", mangohud_manifest_filename_32="mango32.json",
            vkbasalt_manifest_filename_64="vkb64.json", vkbasalt_manifest_filename_32="vkb32.json",
            armada_device_env=self.root / "device", armada_game_launch=self.root / "launch",
            frame_os_layer_dir=self.layer_dir,
        )

    def tearDown(self):
        self._temp.cleanup()

    def _install(self, marker=True, manifest=True):
        if marker:
            self.marker.parent.mkdir(parents=True, exist_ok=True)
            self.marker.write_text("act\n")
        if manifest:
            self.layer_dir.mkdir(parents=True, exist_ok=True)
            (self.layer_dir / FRAME_OS_MANIFEST_FILENAME).write_text("{}\n")

    def _launch_env(self, renderer=True, inherited=""):
        script = "\n".join([
            f"mako_renderer_required={1 if renderer else 0}",
            *layer_environment_lines(self.ctx),
            'printf "IL=%s\\nIMPLICIT=%s\\nGFG=%s\\nDISABLE=%s\\nENABLE_MAKO=%s\\nSHM=%s\\n" '
            '"${VK_INSTANCE_LAYERS-}" "${VK_IMPLICIT_LAYER_PATH-}" "${GFG_FRAME_OS-unset}" '
            '"${DISABLE_GFG_FRAME_OS-}" "${ENABLE_MAKO-unset}" "${GFG_FRAME_OS_SHM-}"',
        ])
        env = {"PATH": os.environ["PATH"], "HOME": str(self.root), "GFG_FRAME_OS": "1"}
        if inherited:
            env["VK_INSTANCE_LAYERS"] = inherited
        out = subprocess.run(["bash", "-c", script], env=env, check=True, capture_output=True, text=True).stdout
        return dict(line.split("=", 1) for line in out.splitlines() if "=" in line)

    def test_pacer_goes_first_above_the_renderer(self):
        self._install()
        env = self._launch_env()
        self.assertEqual(env["IL"].split(":")[:2], [FRAME_OS_LAYER_NAME, "VK_LAYER_MAKO_render"])
        self.assertIn(str(self.layer_dir), env["IMPLICIT"].split(":"))
        self.assertEqual(env["GFG"], "unset")          # never through the implicit gate
        self.assertEqual(env["ENABLE_MAKO"], "unset")  # nor the renderer
        self.assertEqual(env["SHM"], "/dev/shm/gfg-frame-os")

    def test_inherited_copy_is_removed(self):
        self._install()
        env = self._launch_env(inherited=f"VK_LAYER_other:{FRAME_OS_LAYER_NAME}")
        self.assertEqual(env["IL"].split(":").count(FRAME_OS_LAYER_NAME), 1)
        self.assertEqual(env["IL"].split(":")[0], FRAME_OS_LAYER_NAME)
        self.assertIn("VK_LAYER_other", env["IL"])

    def test_off_without_marker_or_without_layer(self):
        for marker, manifest in ((False, True), (True, False)):
            with self.subTest(marker=marker, manifest=manifest):
                for path in (self.marker, self.layer_dir / FRAME_OS_MANIFEST_FILENAME):
                    if path.exists():
                        path.unlink()
                self._install(marker=marker, manifest=manifest)
                env = self._launch_env(inherited=FRAME_OS_LAYER_NAME)
                self.assertNotIn(FRAME_OS_LAYER_NAME, env["IL"])
                self.assertNotIn(str(self.layer_dir), env["IMPLICIT"])
                self.assertEqual(env["GFG"], "unset")
                self.assertEqual(env["DISABLE"], "1")

    def test_renderer_off_still_loads_the_pacer_alone(self):
        self._install()
        env = self._launch_env(renderer=False)
        self.assertEqual(env["IL"], FRAME_OS_LAYER_NAME)


if __name__ == "__main__":
    unittest.main()
