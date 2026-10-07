import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "py_modules"))

from gfg_plugin.frame_os import layer_install  # noqa: E402


class LayerInstallTests(unittest.TestCase):
    def setUp(self):
        self._temp = tempfile.TemporaryDirectory()
        root = Path(self._temp.name)
        self.source = layer_install.bundled_dir(root / "plugin")
        self.target = layer_install.target_dir(root / "share" / "vulkan" / "implicit_layer.d")
        self.log = mock.Mock()

    def tearDown(self):
        self._temp.cleanup()

    def _bundle(self, library=b"ELF-1"):
        self.source.mkdir(parents=True, exist_ok=True)
        (self.source / layer_install.LIBRARY).write_bytes(library)
        (self.source / layer_install.MANIFEST).write_text('{"layer": {}}\n')

    def test_target_is_outside_the_implicit_directory(self):
        self.assertEqual(self.target.name, "gfg-frame-os")
        self.assertNotEqual(self.target.parent.name, "implicit_layer.d")

    def test_build_without_the_layer_stays_inert(self):
        result = layer_install.stage(self.source, self.target, self.log)
        self.assertFalse(result["installed"])
        self.assertIn("does not include", result["error"])
        self.assertFalse(self.target.exists())

    def test_stage_copies_once_and_refreshes_on_update(self):
        self._bundle()
        first = layer_install.stage(self.source, self.target, self.log)
        self.assertEqual((first["installed"], first["changed"], first["error"]), (True, True, None))
        self.assertEqual((self.target / layer_install.LIBRARY).read_bytes(), b"ELF-1")
        self.assertFalse(layer_install.stage(self.source, self.target, self.log)["changed"])
        self._bundle(b"ELF-2")                               # plugin update
        self.assertTrue(layer_install.stage(self.source, self.target, self.log)["changed"])
        self.assertEqual((self.target / layer_install.LIBRARY).read_bytes(), b"ELF-2")

    def test_registered_manifest_points_at_the_private_library_and_stays_gated(self):
        import json
        self._bundle()
        self.source.joinpath(layer_install.MANIFEST).write_text(json.dumps(
            {"file_format_version": "1.2.1", "layer": {"name": "VK_LAYER_GFG_pacer", "library_path": "./x.so"}}))
        registry = self.target.parent / "registry"
        self.assertIsNone(layer_install.stage(self.source, self.target, self.log, registry_dir=registry)["error"])
        layer = json.loads((registry / layer_install.REGISTERED_MANIFEST).read_text())["layer"]
        self.assertEqual(layer["library_path"], str(self.target / layer_install.LIBRARY))
        self.assertEqual(layer["enable_environment"], {"GFG_FRAME_OS": "1"})
        self.assertEqual(layer["library_arch"], "64")
        layer_install.remove(self.target, registry)
        self.assertFalse((registry / layer_install.REGISTERED_MANIFEST).exists())

    def test_remove_takes_the_manifest_and_the_directory(self):
        self._bundle()
        layer_install.stage(self.source, self.target, self.log)
        layer_install.remove(self.target)
        self.assertFalse(self.target.exists())
        layer_install.remove(self.target)                    # idempotent


if __name__ == "__main__":
    unittest.main()
