"""Native Temporal Engine bootstrap contract checks.

Static tests check that the transitional source rewrite has anchored changes.
Full compilation, Vulkan validation, and real-frame fallback belong to CI
and the target-device protocol; this module makes no runtime claims.
"""
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parent.parent
MODULE = ROOT / "engine/gfg-native/bootstrap.py"
spec = importlib.util.spec_from_file_location("gfg_native_bootstrap", MODULE)
bootstrap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bootstrap)


class BootstrapTests(unittest.TestCase):
    def test_checked_replace_unique(self):
        self.assertEqual(bootstrap.checked_replace("abc abcdef", "abcdef", "XYZ", "demo"), "abc XYZ")
        with self.assertRaises(ValueError):
            bootstrap.checked_replace("same same", "same", "a", "demo")
        with self.assertRaises(ValueError):
            bootstrap.checked_replace("hello", "missing", "a", "demo")

    def test_backend_native_has_no_model_registry_path(self):
        before = """    this->m_impl = std::make_unique<InstanceImpl>(
        selectFunc, shaderDllPath, allowLowPrecision
    );
    // GFG Temporal Engine: its own device on the same GPU, created here so the
    // caller's layer-disabling environment also covers it.  Off unless asked.
    const auto& backendVulkan = this->m_impl->getVulkan();
    this->m_temporal = gfg_temporal::Runtime::create(
        gfg_temporal::parseMode(std::getenv("GFG_TEMPORAL_ENGINE")),
        backendVulkan.physdev(), backendVulkan.fi().GetPhysicalDeviceProperties2);
"""
        mock = (
            before
            + 'bool Instance::supportsPackedHdr10Transport() const {\n    const auto& vk = this->m_impl->getVulkan();\n'
            + 'bool Instance::supportsSourceImageLayout(const SourceImageLayout layout) const {\n    const auto format = nativeSourceImageFormat(FrameEncoding::Sdr8, layout);\n'
            + '            return *result;\n        }\n    }\n    const auto& vulkan = this->m_impl->getVulkan();\n'
        )
        patched = bootstrap.patch_backend(mock)
        self.assertIn('temporalMode == gfg_temporal::Mode::Experimental', patched)
        self.assertLess(patched.index("if (temporalMode =="), patched.index("this->m_impl ="))
        self.assertIn('bootstrap.physdev()', patched)
        self.assertIn('LSFG fallback disabled', patched)
        self.assertIn('if (!this->m_impl) return false', patched)
        with self.assertRaises(ValueError):
            bootstrap.patch_backend(patched)

    def test_renderer_no_dll_lookup_in_native_mode(self):
        mock = (
            '    const auto& global = this->config.get().global();\n\n'
            '    std::optional<std::filesystem::path> scalingShaderDll;\n'
            '    if (info.spatialScalingActive) {\n'
            '            std::string dll{};\n'
            '            if (global.dll.has_value())\n'
            '                dll = *global.dll;\n'
            '            else\n'
            '                dll = ls::findShaderDll();\n\n'
            '            const auto applicationDevice = identifyApplicationDevice(vk);\n'
            '            if (frameGenerationRequested && !info.spatialScalingActive)\n'
            '                throw ls::error("failed to create backend instance", e);\n'
        )
        patched = bootstrap.patch_renderer(mock)
        self.assertIn('if (!nativeRequested)', patched)
        self.assertIn('info.spatialScalingActive && !nativeRequested', patched)
        self.assertIn('&&\n                    !nativeRequested)', patched)
        with self.assertRaises(ValueError):
            bootstrap.patch_renderer(patched)


if __name__ == "__main__":
    unittest.main()
