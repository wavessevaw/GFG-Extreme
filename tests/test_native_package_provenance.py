"""The experimental package includes source but never generated build trees."""
import importlib.util
from pathlib import Path
import tempfile
import subprocess
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "package_native_fg", ROOT / "scripts/package_native_fg.py"
)
package_native_fg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(package_native_fg)


class PackageSourceTests(unittest.TestCase):
    def test_changed_corresponding_build_helper_cannot_claim_clean_commit(self):
        with tempfile.TemporaryDirectory(prefix="gfg-package-git-") as temp:
            root = Path(temp)
            helper = root / "scripts/build_native_steam_abi.sh"
            helper.parent.mkdir(); helper.write_text("original\n")
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            subprocess.run(["git", "add", "."], cwd=root, check=True)
            subprocess.run(["git", "-c", "user.name=Package Test", "-c", "user.email=package@example.invalid",
                            "commit", "-qm", "source"], cwd=root, check=True)
            files = {"SOURCE/scripts/build_native_steam_abi.sh": helper.read_bytes()}
            with patch.object(package_native_fg, 'ROOT', root):
                self.assertFalse(package_native_fg.worktree_dirty(files))
                helper.write_text("changed flags\n")
                self.assertTrue(package_native_fg.worktree_dirty(files))

    def test_all_native_build_variants_are_excluded_from_source_bundle(self):
        with tempfile.TemporaryDirectory(prefix="gfg-package-source-") as temp:
            root = Path(temp)
            native = root / "engine/gfg-native"
            temporal = root / "engine/gfg-temporal"
            for path in (
                native / "src/gpu_bridge.c",
                native / "Makefile",
                temporal / "src/te_engine.c",
                temporal / "Makefile",
            ):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("source\n")
            generated = ("build", "build-te", "build-pass", "build-cpu", "build_release")
            for base in (native, temporal):
                for name in generated:
                    path = base / name / "accidental-source.c"
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text("generated\n")

            original_root = package_native_fg.ROOT
            package_native_fg.ROOT = root
            try:
                selected = package_native_fg.source_files()
            finally:
                package_native_fg.ROOT = original_root

            self.assertIn("SOURCE/engine/gfg-native/src/gpu_bridge.c", selected)
            self.assertIn("SOURCE/engine/gfg-temporal/src/te_engine.c", selected)
            self.assertFalse(any("accidental-source.c" in path for path in selected))


if __name__ == "__main__":
    unittest.main()
