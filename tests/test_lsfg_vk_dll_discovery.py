"""Owner-installed LSFG-VK 2.x resource discovery; never ship proprietary DLLs."""
import logging
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "py_modules"))
decky = types.ModuleType("decky")
decky.logger = logging.getLogger("lsfg-vk-discovery-test")
decky.DECKY_USER_HOME = "/tmp/gfg-lsfg-discovery-unused"
sys.modules.setdefault("decky", decky)

from gfg_plugin.dll_detection import DllDetectionService


class LsfgVkDllDiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="lsfg-vk-resource-")
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        with patch("gfg_plugin.base_service.resolve_user_home", return_value=self.home):
            self.detector = DllDetectionService()
        self.env = patch.dict(os.environ, {}, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_lossless_legacy_dll_is_not_2x_resource(self):
        loc = self.home / ".local/share/Steam/steamapps/common/Lossless Scaling"
        loc.mkdir(parents=True)
        (loc / "Lossless.dll").write_bytes(b"MZ legacy model")
        status = self.detector.check_lsfg_vk_dll()
        self.assertFalse(status["detected"])
        self.assertIsNone(status["path"])
        self.assertIn("lsfg-vk.dll", status["message"])

    def test_adjacent_original_lsfg_vk_resource_is_detected(self):
        loc = self.home / ".local/share/Steam/steamapps/common/Lossless Scaling"
        loc.mkdir(parents=True)
        (loc / "Lossless.dll").write_bytes(b"MZ legacy model")
        resource = loc / "lsfg-vk.dll"
        resource.write_bytes(b"MZ resource")
        status = self.detector.check_lsfg_vk_dll()
        self.assertTrue(status["detected"])
        self.assertEqual(status["path"], str(resource))

    def test_explicit_legacy_name_maps_to_adjacent_2x_resource(self):
        loc = self.home / "custom"
        loc.mkdir()
        (loc / "Lossless.dll").write_bytes(b"MZ legacy")
        resource = loc / "lsfg-vk.dll"
        resource.write_bytes(b"MZ model")
        with patch.dict(os.environ, {"GFG_LSFG_DLL_PATH": str(loc / "Lossless.dll")}):
            self.assertEqual(self.detector.check_lsfg_vk_dll()["path"], str(resource))
        resource.unlink()
        with patch.dict(os.environ, {"GFG_LSFG_DLL_PATH": str(loc / "Lossless.dll")}):
            self.assertFalse(self.detector.check_lsfg_vk_dll()["detected"])

    def test_secondary_steam_library_and_case_correct_name(self):
        sd = self.home / "secondary-library"
        loc = sd / "steamapps/common/Lossless Scaling"
        loc.mkdir(parents=True)
        resource = loc / "lsfg-vk.dll"
        resource.write_bytes(b"MZ model")
        with patch.object(self.detector, "_get_steam_library_paths", return_value=[str(sd)]):
            status = self.detector.check_lsfg_vk_dll()
        self.assertTrue(status["detected"])
        self.assertEqual(status["path"], str(resource))


if __name__ == "__main__":
    unittest.main()
