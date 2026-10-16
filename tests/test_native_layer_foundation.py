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
        self.assertIn("TE stages frame=", bridge)
        self.assertIn("upload_ms=", bridge)
        self.assertIn("submit_ms=", bridge)
        self.assertIn("download_ms=", bridge)
        self.assertIn("CPU convert frame=", bridge)
        self.assertIn("process breaker: skip CPU bridge", bridge)
        self.assertIn("process_cpu_bridge_slow", bridge)

    def test_host_cached_vulkan_readback_and_bulk_mapped_transfer(self):
        bridge = (ENGINE / "src/cpu_bridge.c").read_text()
        policy = (ENGINE / "src/memory_policy.h").read_text()
        self.assertIn("VK_MEMORY_PROPERTY_HOST_CACHED_BIT", policy)
        self.assertIn("gfg_native_readback_memory_type", bridge)
        self.assertIn("memcpy(fg->rgba_cached,fg->mapped,pixels*COLOR_BPP)", bridge)
        self.assertIn("memcpy(fg->mapped,fg->rgba_cached,pixels*COLOR_BPP)", bridge)
        self.assertIn("memcpy_from_gpu_ms=", bridge)
        self.assertIn("swizzle_ms=", bridge)
        self.assertIn("staging memory type=", bridge)
        self.assertIn("free(fg->rgba_cached)", bridge)
        self.assertIn('disable_slow_bridge(fg,"before-real-present"', bridge)

    def test_present_wait_monitor_serializes_swapchain_host_access(self):
        code = (ENGINE / "src/layer.c").read_text()
        monitor = code.split("static void *native_monitor_main", 1)[1].split(
            "static uint64_t native_ids_assign", 1)[0]
        present = code.split("native_QueuePresentKHR(VkQueue queue", 1)[1].split(
            "#ifdef GFG_NATIVE_WITH_TE\nstatic native_present_ids *native_find_ids", 1)[0]
        self.assertIn("pthread_mutex_t wsi_lock", code)
        self.assertIn('d->present_trace = native_env_is_1("GFG_NATIVE_PRESENT_TRACE")', code)
        self.assertIn("native_ids_driver_wait(ids, id, 0)", monitor)
        self.assertIn("pthread_mutex_lock(&ids->wsi_lock)", monitor)
        acquire = code.split("native_AcquireNextImageKHR(", 1)[1].split(
            "native_AcquireNextImage2KHR(", 1)[0]
        acquire2 = code.split("native_AcquireNextImage2KHR(", 1)[1].split(
            "native_QueuePresentKHR(", 1)[0]
        self.assertIn("pthread_mutex_lock(&ids->wsi_lock)", acquire)
        self.assertIn("pthread_mutex_lock(&ids->wsi_lock)", acquire2)
        self.assertIn("pthread_mutex_lock(&sync_ids->wsi_lock)", present)
        self.assertIn("pthread_mutex_unlock(&sync_ids->wsi_lock)", present)
        wait = code.split("native_WaitForPresentKHR(", 1)[1].split(
            "native_WaitForPresent2KHR(", 1)[0]
        self.assertIn("pthread_mutex_lock(&ids->wsi_lock)", wait)
        wait2 = code.split("native_WaitForPresent2KHR(", 1)[1].split(
            "#endif", 1)[0]
        self.assertIn("pthread_mutex_lock(&ids->wsi_lock)", wait2)

if __name__ == "__main__":
    unittest.main()
