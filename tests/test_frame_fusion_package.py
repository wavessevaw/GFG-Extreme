"""A forked native archive must carry its own identity and preserve legacy payloads."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import tarfile
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("fusion_package", ROOT / "scripts/package_frame_fusion.py")
module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)


class PackageTests(unittest.TestCase):
    def setup_package(self, temp):
        plugin = Path(temp) / "plugin"; build = Path(temp) / "build"
        (plugin / "bin").mkdir(parents=True)
        (plugin / "engine/gfg-fusion").mkdir(parents=True)
        shutil.copy2(ROOT / "package.json", plugin / "package.json")
        for name in ("renderer.patch", "source.json"):
            shutil.copy2(ROOT / "engine/gfg-fusion" / name, plugin / "engine/gfg-fusion" / name)
        archive = "MAKO-Renderer-v4.0.0-linux.tar.xz"
        shutil.copy2(ROOT / "bin" / archive, plugin / "bin" / archive)
        shutil.copy2(ROOT / "bin/SHA256SUMS.txt", plugin / "bin/SHA256SUMS.txt")
        for i, path in enumerate(("mako-render/libmako-render.so", "mako-render/libmako-render-scaling.so",
                "mako-cli/mako-cli", "mako-render/gfg-frame-fusion-tests")):
            file = build / path; file.parent.mkdir(parents=True, exist_ok=True)
            file.write_bytes(b"\x7fELF\x02\x01" + b"\0" * 12 + b"\x3e\x00" + bytes([i]) * 128)
        return plugin, build

    def test_local_archive_identity_and_unchanged_32bit_payloads(self):
        with tempfile.TemporaryDirectory() as temp:
            plugin, build = self.setup_package(temp)
            with tarfile.open(plugin / "bin/MAKO-Renderer-v4.0.0-linux.tar.xz") as archive:
                old32 = archive.extractfile("lib32/libmako-render.so").read()
            module.package(plugin, build)
            metadata = json.loads((plugin / "package.json").read_text())
            self.assertNotIn("remote_binary", metadata)
            bundle = metadata["bundled_renderer"]
            identity = json.loads((plugin / "bin/gfg-fusion/manifest.json").read_text())
            payload = (plugin / "bin" / bundle["name"]).read_bytes()
            self.assertEqual(hashlib.sha256(payload).hexdigest(), bundle["sha256hash"])
            self.assertEqual(identity["archive_sha256"], bundle["sha256hash"])
            with tarfile.open(fileobj=io.BytesIO(payload)) as archive:
                self.assertEqual(archive.extractfile("lib32/libmako-render.so").read(), old32)
                self.assertEqual(archive.extractfile("lib/libmako-render.so").read(),
                    (build / "mako-render/libmako-render.so").read_bytes())
            self.assertFalse(identity["default_enabled"])

    def test_invalid_architecture_never_replaces_the_archive(self):
        with tempfile.TemporaryDirectory() as temp:
            plugin, build = self.setup_package(temp)
            archive = plugin / "bin/MAKO-Renderer-v4.0.0-linux.tar.xz"
            original = archive.read_bytes()
            (build / "mako-render/libmako-render.so").write_bytes(b"not an ELF")
            with self.assertRaises(ValueError): module.package(plugin, build)
            self.assertEqual(archive.read_bytes(), original)

    def test_source_patch_mismatch_never_packages(self):
        with tempfile.TemporaryDirectory() as temp:
            plugin, build = self.setup_package(temp)
            (plugin / "engine/gfg-fusion/renderer.patch").write_text("different patch")
            with self.assertRaises(ValueError): module.package(plugin, build)
