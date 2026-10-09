"""Release ZIP validation uses the packaged bytes, not checkout metadata."""
import importlib.util
import io
import hashlib
import json
import unittest
import zipfile
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "check_release_archive", Path(__file__).resolve().parents[1] / "scripts/check_release_archive.py")
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


class ReleaseArchiveTests(unittest.TestCase):
    def files(self):
        files = {
            "package.json": json.dumps({"version": "1.6.6"}),
            "package-lock.json": json.dumps({"version": "1.6.6", "packages": {"": {"version": "1.6.6"}}}),
            "py_modules/gfg_plugin/governor_service.py": 'VERSION = "1.6.6"\n',
            "py_modules/gfg_plugin/log_report.py": 'CURRENT_VERSION = "1.6.6"\n',
            "dist/index.js": "frontend",
            "main.py": "backend",
        }
        for layer in ("pacer", "hud"):
            library = f"libVkLayer_gfg_{layer}.so"
            files[f"bin/gfg-frame-os/{library}"] = b"\x7fELF\x02\x01" + bytes(12) + b"\x3e\x00"
            files[f"bin/gfg-frame-os/VkLayer_gfg_{layer}.json"] = json.dumps(
                {"layer": {"library_path": "./" + library}})
        native = b"\x7fELF\x02\x01" + bytes(12) + b"\x3e\x00" + b"GFG Open: backend=color-flow-v1"
        manifest = json.dumps({"layer": {"library_path": "./libmako-render.so"}}).encode()
        files["bin/gfg-open/libmako-render.so"] = native
        files["bin/gfg-open/VkLayer_MAKO_render.json"] = manifest
        files["bin/gfg-open/SHA256SUMS"] = "\n".join(
            hashlib.sha256(data).hexdigest() + "  " + name
            for name, data in (("libmako-render.so", native), ("VkLayer_MAKO_render.json", manifest))) + "\n"
        return files

    def archive(self, files):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            for name, content in files.items():
                archive.writestr("GFG-Extreme/" + name, content)
        buffer.seek(0)
        return buffer

    def test_valid_archive(self):
        validator.check(self.archive(self.files()), "1.6.6")

    def test_stale_packaged_version(self):
        files = self.files()
        files["package.json"] = '{"version": "1.6.5"}'
        with self.assertRaisesRegex(ValueError, "version mismatch"):
            validator.check(self.archive(files), "1.6.6")

    def test_unsafe_archive_path(self):
        files = self.files()
        files["../outside"] = "bad"
        with self.assertRaisesRegex(ValueError, "unsafe"):
            validator.check(self.archive(files), "1.6.6")

    def test_wrong_native_architecture(self):
        files = self.files()
        files["bin/gfg-frame-os/libVkLayer_gfg_hud.so"] = b"not ELF"
        with self.assertRaisesRegex(ValueError, "not a 64-bit"):
            validator.check(self.archive(files), "1.6.6")

    def test_missing_layer(self):
        files = self.files()
        del files["bin/gfg-frame-os/libVkLayer_gfg_pacer.so"]
        with self.assertRaises(KeyError):
            validator.check(self.archive(files), "1.6.6")

    def test_corrupted_open_generator(self):
        files = self.files()
        files["bin/gfg-open/libmako-render.so"] += b"corrupt"
        with self.assertRaisesRegex(ValueError, "checksum mismatch"):
            validator.check(self.archive(files), "1.6.6")
