"""Isolated installer transactions: never touch the developer's installation."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class NativeGpuInstallTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="gfg-native-install-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.pkg = self.root / "package"
        self.pkg.mkdir()
        self.home = self.root / "home"
        self.home.mkdir()
        self.env = dict(os.environ, HOME=str(self.home), XDG_DATA_HOME=str(self.home / "data"))
        for name in ("GFG_NATIVE_FG", "GFG_NATIVE_GPU", "GFG_NATIVE_MODE", "GFG_NATIVE_CPU_BRIDGE",
                     "DISABLE_GFG_NATIVE_FG", "VK_INSTANCE_LAYERS", "VK_LAYER_PATH"):
            self.env.pop(name, None)
        for file in (ROOT / "engine/gfg-native/package").glob("*.sh"):
            shutil.copy2(file, self.pkg / file.name)
        (self.pkg / "libVkLayer_gfg_native.so").write_bytes(b"fixture payload for installer only")
        shutil.copy2(ROOT / "engine/gfg-native/VkLayer_gfg_native.json", self.pkg)
        self.checksums()
        self.target = self.home / "data/gfg-native"
        self.launcher = self.home / ".local/bin/gfg-native"

    def checksums(self):
        (self.pkg / "SHA256SUMS.txt").write_text("".join(
            f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n"
            for p in sorted(self.pkg.iterdir()) if p.name != "SHA256SUMS.txt"))

    def run_script(self, name, check=True):
        return subprocess.run(["bash", str(self.pkg / name)], env=self.env, text=True,
                              capture_output=True, check=check)

    def launch(self, *args, env=None):
        return subprocess.run([str(self.launcher), *args], env=env or self.env,
                              text=True, capture_output=True, check=True).stdout

    def test_upgrade_rollback_restores_exact_previous_files(self):
        self.target.mkdir(parents=True)
        self.launcher.parent.mkdir(parents=True)
        previous = {self.target / "libVkLayer_gfg_native.so": b"previous ELF\0",
                    self.target / "VkLayer_gfg_native.json": b"previous manifest",
                    self.launcher: b"#!/bin/sh\nprintf 'previous launcher'\n"}
        for p, data in previous.items():
            p.write_bytes(data)
            p.chmod(0o750)
        self.run_script("install.sh")
        self.assertNotEqual(self.launcher.read_bytes(), previous[self.launcher])
        self.run_script("rollback.sh")
        for p, data in previous.items():
            self.assertEqual(p.read_bytes(), data)
            self.assertEqual(p.stat().st_mode & 0o777, 0o750)

    def test_corrupted_payload_does_not_mutate_existing_install(self):
        self.run_script("install.sh")
        before = {p.relative_to(self.home): p.read_bytes() for p in self.home.rglob("*") if p.is_file()}
        (self.pkg / "libVkLayer_gfg_native.so").write_bytes(b"corrupted")
        self.assertNotEqual(self.run_script("install.sh", check=False).returncode, 0)
        after = {p.relative_to(self.home): p.read_bytes() for p in self.home.rglob("*") if p.is_file()}
        self.assertEqual(before, after)

    def test_off_mode_preserves_arguments_and_disables_native(self):
        self.run_script("install.sh")
        args = ["space argument", "$(literal)", ""]
        program = "import json,os,sys; print(json.dumps([sys.argv[1:],os.getenv('DISABLE_GFG_NATIVE_FG'),os.getenv('GFG_NATIVE_GPU')]))"
        output = self.launch("--off", shutil.which("python3"), "-c", program, *args)
        self.assertEqual(json.loads(output), [args, "1", None])
        enabled_env = dict(self.env, DISABLE_GFG_NATIVE_FG="1")
        output = self.launch("/usr/bin/env", env=enabled_env)
        self.assertIn("GFG_NATIVE_GPU=1\n", output)
        self.assertNotIn("DISABLE_GFG_NATIVE_FG=", output)

    def test_first_install_rollback_and_uninstall_leave_working_launch_option(self):
        for cleanup in ("rollback.sh", "uninstall.sh"):
            self.run_script("install.sh")
            self.run_script(cleanup)
            self.assertFalse((self.target / "libVkLayer_gfg_native.so").exists())
            self.assertFalse((self.target / "VkLayer_gfg_native.json").exists())
            self.assertEqual(self.launch("/usr/bin/printf", "%s", "a b"), "a b")


if __name__ == "__main__":
    unittest.main()
