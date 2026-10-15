import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parent.parent
ENGINE = ROOT / "engine/gfg-native"

class NativeLayerTests(unittest.TestCase):
    def test_manifest_is_opt_in_and_standalone(self):
        payload = json.loads((ENGINE / "VkLayer_gfg_native.json").read_text())
        self.assertEqual(payload["layer"]["name"], "VK_LAYER_GFG_native")
        self.assertEqual(payload["layer"]["enable_environment"], {"GFG_NATIVE_FG": "1"})
        self.assertEqual(payload["layer"]["library_path"], "./libVkLayer_gfg_native.so")
        self.assertIn("pass-through", payload["layer"]["description"])

    def test_no_foreign_backend_linkage(self):
        code = (ENGINE / "src/layer.c").read_text()
        make = (ENGINE / "Makefile").read_text()
        # We intentionally do not use MAKO, DLL, or LSFG symbols in the WSI code.
        for symbol in ("mako::", "loadDllResourceArchive(", "lsfg_", "dlopen(", "Lossless.dll\""):
            self.assertNotIn(symbol, code)
        self.assertNotIn("-lmako", make)
        self.assertIn("native_QueuePresentKHR", code)
        self.assertIn("d->present(queue, info)", code)
        self.assertIn("output=real-only", code)
        self.assertIn("VK_IMAGE_USAGE_TRANSFER_SRC_BIT", code)
        self.assertIn("VK_IMAGE_USAGE_TRANSFER_DST_BIT", code)

if __name__ == "__main__":
    unittest.main()
