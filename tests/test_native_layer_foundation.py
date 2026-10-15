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
        self.assertIn("VK_FORMAT_B8G8R8A8_SRGB", code)
        self.assertIn("VK_FORMAT_R8G8B8A8_SRGB", code)
        self.assertIn('reason ? reason : "accepted"', code)
        self.assertIn('"missing-transfer-src-or-dst-support"', code)
        self.assertIn("GFG_NATIVE_CPU_BRIDGE", code)
        self.assertIn("gfg_cpu_fg_present", code)
        self.assertIn("native_GetDeviceQueue", code)
        self.assertIn("native_AcquireNextImageKHR", code)
        self.assertIn("native_AcquireNextImage2KHR", code)
        self.assertIn("native_acquired(", code)
        self.assertIn("if (!strcmp(symbol, \"vkQueuePresentKHR\"))", code)


    def test_native_cpu_path_uses_only_internal_temporal_engine(self):
        bridge = (ENGINE / "src/cpu_bridge.c").read_text()
        for forbidden in ("mako::", "lsfg_", "libmako", "dlopen("):
            self.assertNotIn(forbidden, bridge)
        self.assertIn("te_submit_frame(", bridge)
        self.assertIn("te_download_rgb(", bridge)
        self.assertIn("vkQueuePresentKHR", (ENGINE / "src/layer.c").read_text())
        self.assertIn("VK_IMAGE_LAYOUT_PRESENT_SRC_KHR", bridge)
        self.assertIn("is_bgra_format", bridge)
        self.assertIn("VK_FORMAT_B8G8R8A8_SRGB", bridge)
        self.assertIn("VK_FORMAT_R8G8B8A8_SRGB", bridge)

    def test_wsi_present_semaphores_are_per_swapchain_image(self):
        bridge = (ENGINE / "src/cpu_bridge.c").read_text()
        self.assertIn("VkSemaphore *ready_per_image", bridge)
        self.assertIn("fg->ready_per_image[idx]", bridge)
        self.assertIn("submit_wait(fg,1,&fg->acquire_sem,present_ready)", bridge)
        present = bridge.split("static bool present_generated(", 1)[1].split(
            "gfg_cpu_fg *gfg_cpu_fg_create(", 1)[0]
        self.assertNotIn("QueueWaitIdle", present)
        self.assertIn("if (distinct)", bridge)
        self.assertIn("watchdog disabled generator", bridge)
        self.assertIn("GFG_NATIVE_MAX_FRAME_MS", bridge)
        self.assertIn("capture_ms=", bridge)

if __name__ == "__main__":
    unittest.main()
