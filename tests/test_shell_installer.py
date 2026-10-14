"""GFG Shell installer: pinned runtime, SHA-256 check, user-home only, atomic replace."""
import hashlib
import io
import json
import os
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'py_modules'))
from gfg_plugin.shell_installer import ShellInstaller

BIN = "Godot_v4.4.1-stable_linux.x86_64"
URL = "https://github.com/godotengine/godot/releases/download/4.4.1-stable/" + BIN + ".zip"


def runtime_zip(payload=b"\x7fELF fake godot"):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(BIN, payload)
    return buf.getvalue()


class FakeResponse(io.BytesIO):
    def __init__(self, data):
        super().__init__(data)
        self.headers = {"Content-Length": str(len(data))}

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.home = root / "home"
        self.home.mkdir()
        self.pkg = root / "pkg"
        (self.pkg / "licenses").mkdir(parents=True)
        for name in ("gfg-shell.pck", "gfg-shell.sh", "uninstall.sh", "collect-diagnostics.sh"):
            (self.pkg / name).write_text(name)
        (self.pkg / "VERSION").write_text("0.1.0\n")
        (self.pkg / "licenses" / "GODOT-LICENSE.txt").write_text("MIT")
        self.zip = runtime_zip()
        self.spec = {"version": "4.4.1-stable", "url": URL, "sha256": hashlib.sha256(self.zip).hexdigest(), "bin": BIN}
        (self.pkg / "godot.json").write_text(json.dumps(self.spec))
        self.downloads = []

    def tearDown(self):
        self.tmp.cleanup()

    def opener(self, url, timeout):
        self.downloads.append(url)
        return FakeResponse(self.zip)

    def inst(self):
        return ShellInstaller(self.home, self.pkg, opener=self.opener, uid=None)

    def app(self):
        return self.home / ".local/share/gfg-shell/app"

    def test_status_before_install(self):
        st = self.inst().status()
        self.assertTrue(st["packaged"])
        self.assertFalse(st["installed"])
        self.assertEqual(st["packaged_version"], "0.1.0")
        self.assertTrue(st["path"].endswith(".local/share/gfg-shell/app/gfg-shell.sh"))

    def test_install_downloads_verifies_and_installs(self):
        r = self.inst().install()
        self.assertTrue(r["success"], r)
        self.assertEqual(self.downloads, [URL])
        self.assertEqual((self.app() / "bin/godot").read_bytes(), b"\x7fELF fake godot")
        self.assertTrue(os.access(self.app() / "bin/godot", os.X_OK))
        self.assertTrue(os.access(self.app() / "gfg-shell.sh", os.X_OK))
        self.assertEqual((self.app() / "licenses/GODOT-LICENSE.txt").read_text(), "MIT")
        st = self.inst().status()
        self.assertTrue(st["installed"])
        self.assertFalse(st["update_available"])
        self.assertEqual(st["runtime_version"], "4.4.1-stable")
        self.assertFalse(any(p.name.startswith(".install-") for p in self.app().parent.iterdir()))

    def test_update_reuses_runtime_without_download(self):
        self.inst().install()
        (self.pkg / "VERSION").write_text("0.2.0\n")
        (self.pkg / "gfg-shell.pck").write_text("new")
        self.assertTrue(self.inst().status()["update_available"])
        self.assertTrue(self.inst().install()["success"])
        self.assertEqual(len(self.downloads), 1)
        self.assertEqual((self.app() / "gfg-shell.pck").read_text(), "new")
        self.assertFalse(self.inst().status()["update_available"])

    def test_bad_checksum_installs_nothing(self):
        self.zip = runtime_zip(b"tampered")
        r = self.inst().install()
        self.assertFalse(r["success"])
        self.assertIn("SHA-256", r["error"])
        self.assertFalse(self.app().exists())

    def test_failed_update_keeps_previous_install(self):
        self.inst().install()
        self.spec["version"] = "9.9-stable"   # forces a new download ...
        (self.pkg / "godot.json").write_text(json.dumps(self.spec))
        self.zip = runtime_zip(b"tampered")   # ... that fails its checksum
        self.assertFalse(self.inst().install()["success"])
        self.assertEqual((self.app() / "bin/godot").read_bytes(), b"\x7fELF fake godot")

    def test_network_error_is_reported(self):
        def broken(url, timeout):
            raise TimeoutError("timed out")
        r = ShellInstaller(self.home, self.pkg, opener=broken, uid=None).install()
        self.assertFalse(r["success"])
        self.assertIn("timed out", r["error"])

    def test_only_official_godot_url(self):
        self.spec["url"] = "https://example.com/godot.zip"
        (self.pkg / "godot.json").write_text(json.dumps(self.spec))
        r = self.inst().install()
        self.assertFalse(r["success"])
        self.assertEqual(self.downloads, [])

    def test_symlinked_destination_refused(self):
        (self.home / ".local/share").mkdir(parents=True)
        os.symlink(self.tmp.name, self.home / ".local/share/gfg-shell")
        r = self.inst().install()
        self.assertFalse(r["success"])
        self.assertIn("symbolic link", r["error"])

    def test_build_without_shell(self):
        (self.pkg / "VERSION").unlink()
        self.assertFalse(self.inst().status()["packaged"])
        self.assertFalse(self.inst().install()["success"])

    def test_shortcut_memory_and_uninstall(self):
        i = self.inst()
        i.install()
        self.assertFalse(i.set_shortcut("12")["success"])
        self.assertFalse(i.set_shortcut(-1)["success"])
        self.assertTrue(i.set_shortcut(3000000001)["success"])
        self.assertEqual(i.status()["shortcut_appid"], 3000000001)
        self.assertTrue(i.uninstall()["success"])
        st = i.status()
        self.assertFalse(st["installed"])
        self.assertIsNone(st["shortcut_appid"])


if __name__ == "__main__":
    unittest.main()
