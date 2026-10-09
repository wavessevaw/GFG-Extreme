import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "py_modules"))
from gfg_plugin.theme_installer import ThemeInstaller


class ThemeInstallerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.home = self.root / "deck"
        self.home.mkdir()
        self.source = self.root / "bundle"
        self.source.mkdir()
        (self.source / "theme.json").write_text(json.dumps({"name": "GFG Extreme"}))
        (self.source / "shared.css").write_text("body { color: red; }")
        self.service = ThemeInstaller(self.home, self.source)

    def test_install_update_preserves_extras_and_does_not_enable_theme(self):
        self.assertFalse(self.service.status()["installed"])
        self.assertTrue(self.service.install()["success"])
        dest = self.service.destination
        self.assertEqual(dest, self.home / "homebrew/themes/GFG Extreme")
        (dest / "personal.css").write_text("custom")
        (self.source / "shared.css").write_text("body { color: green; }")
        self.assertFalse(self.service.status()["current"])
        self.assertTrue(self.service.install()["success"])
        self.assertEqual((dest / "personal.css").read_text(), "custom")
        self.assertTrue(self.service.status()["current"])
        self.assertEqual(sorted(p.name for p in dest.parent.iterdir()), ["GFG Extreme"])

    def test_failed_commit_restores_previous_theme(self):
        self.service.install()
        old = (self.service.destination / "shared.css").read_text()
        (self.source / "shared.css").write_text("new")
        import gfg_plugin.theme_installer as module
        replace = module.os.replace
        def fail_payload(src, dst):
            if Path(src).name == "GFG Extreme" and Path(src).parent.name.startswith(".gfg-theme-"):
                raise OSError("cannot commit")
            return replace(src, dst)
        with patch.object(module.os, "replace", side_effect=fail_payload):
            self.assertFalse(self.service.install()["success"])
        self.assertEqual((self.service.destination / "shared.css").read_text(), old)
        self.assertEqual(sorted(p.name for p in self.service.destination.parent.iterdir()), ["GFG Extreme"])

    def test_symlink_destination_and_custom_file_are_rejected(self):
        target = self.root / "other"
        target.mkdir()
        (self.home / "homebrew").symlink_to(target, target_is_directory=True)
        self.assertFalse(self.service.install()["success"])
        self.assertEqual(list(target.iterdir()), [])
        (self.home / "homebrew").unlink()
        self.service.install()
        (self.service.destination / "personal.css").symlink_to(self.source / "shared.css")
        self.assertFalse(self.service.install()["success"])

    def test_invalid_or_missing_bundle_leaves_existing_theme(self):
        self.service.install()
        before = (self.service.destination / "theme.json").read_text()
        (self.source / "theme.json").write_text("{}")
        self.assertFalse(self.service.install()["success"])
        self.assertEqual((self.service.destination / "theme.json").read_text(), before)

    def test_shipped_theme_manifest_and_all_patch_files_are_available(self):
        source = ROOT / "themes/css-loader/GFG Extreme"
        with tempfile.TemporaryDirectory() as home:
            service = ThemeInstaller(Path(home), source)
            self.assertTrue(service.install()["success"])
            self.assertTrue(service.status()["current"])
            for css in source.glob("*.css"):
                self.assertEqual(css.read_bytes(), (service.destination / css.name).read_bytes())
