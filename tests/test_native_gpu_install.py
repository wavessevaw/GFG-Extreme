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
        self.env["XDG_STATE_HOME"] = str(self.home / ".local/state")
        for name in ("GFG_NATIVE_FG", "GFG_NATIVE_GPU", "GFG_NATIVE_GPU_BRIDGE", "GFG_NATIVE_ALGO", "GFG_NATIVE_MODE", "GFG_NATIVE_CPU_BRIDGE",
                     "DISABLE_GFG_NATIVE_FG", "VK_INSTANCE_LAYERS", "VK_LAYER_PATH"):
            self.env.pop(name, None)
        for file in (ROOT / "engine/gfg-native/package").glob("*.sh"):
            shutil.copy2(file, self.pkg / file.name)
        shutil.copy2(ROOT / "scripts/accept_report.py", self.pkg)
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
                    self.target / "diagnose.sh": b"previous diagnostics",
                    self.target / "accept_report.py": b"previous report",
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
        program = "import json,os,sys; print(json.dumps([sys.argv[1:],os.getenv('DISABLE_GFG_NATIVE_FG'),os.getenv('GFG_NATIVE_GPU_BRIDGE')]))"
        output = self.launch("--off", shutil.which("python3"), "-c", program, *args)
        self.assertEqual(json.loads(output), [args, "1", None])
        enabled_env = dict(self.env, DISABLE_GFG_NATIVE_FG="1")
        output = self.launch("/usr/bin/env", env=enabled_env)
        self.assertIn("GFG_NATIVE_GPU_BRIDGE=1\n", output)
        self.assertNotIn("DISABLE_GFG_NATIVE_FG=", output)

    def test_off_clears_only_own_layer_and_runs_without_external_helpers(self):
        self.run_script("install.sh")
        env = dict(self.env, GFG_NATIVE_FG="1", GFG_NATIVE_GPU_BRIDGE="1",
                   VK_INSTANCE_LAYERS="foreign.before:VK_LAYER_GFG_native:foreign.after:VK_LAYER_GFG_native",
                   VK_LOADER_LAYERS_ENABLE="foreign.*,VK_LAYER_GFG_native,another",
                   PATH="/nonexistent", GFG_NATIVE_MODE_FILE="/nonexistent/settings")
        program = "import json,os,sys; print(json.dumps([sys.argv[1:],os.getenv('VK_INSTANCE_LAYERS'),os.getenv('VK_LOADER_LAYERS_ENABLE'),os.getenv('GFG_NATIVE_GPU_BRIDGE')])); sys.exit(17)"
        result = subprocess.run(["/bin/bash", str(self.launcher), "--off", shutil.which("python3"),
                                 "-c", program, "", "a b", "$(literal)", "тест"],
                                env=env, text=True, capture_output=True)
        self.assertEqual(result.returncode, 17, result.stderr)
        self.assertEqual(json.loads(result.stdout), [["", "a b", "$(literal)", "тест"],
                         "foreign.before:foreign.after", "foreign.*,another", None])

    def test_telemetry_directory_failure_does_not_prevent_game_start(self):
        self.run_script("install.sh")
        state = self.home / "blocked-state"
        state.write_text("not a directory")
        result = self.launch("/usr/bin/printf", "%s", "game-ran",
                             env=dict(self.env, XDG_STATE_HOME=str(state)))
        self.assertEqual(result, "game-ran")

    def test_unavailable_diagnostic_capture_still_runs_game_and_preserves_status(self):
        self.run_script("install.sh")
        state = self.home / "blocked-state"
        state.write_text("not a directory")
        program = "import sys; print('game-ran'); sys.exit(19)"
        result = subprocess.run([str(self.launcher), "--off", "--diagnose", shutil.which("python3"),
                                 "-c", program], env=dict(self.env, XDG_STATE_HOME=str(state)),
                                text=True, capture_output=True)
        self.assertEqual(result.returncode, 19, result.stderr)
        self.assertIn('game-ran', result.stdout)
        self.assertIn('without capture', result.stderr)

    def test_repeated_staging_keeps_previous_distinct_version_for_rollback(self):
        self.run_script("install.sh")
        previous = self.launcher.read_bytes()
        previous_manifest = b'{"version":"previous"}\n'
        (self.pkg / "MANIFEST.json").write_bytes(previous_manifest)
        self.checksums(); self.run_script("install.sh")
        (self.pkg / "gfg-native.sh").write_text("#!/bin/bash\nexec \"$@\"\n# upgraded\n")
        (self.pkg / "MANIFEST.json").write_text('{"version":"next"}\n')
        self.checksums(); self.run_script("install.sh"); self.run_script("install.sh")
        self.run_script("rollback.sh")
        self.assertEqual(self.launcher.read_bytes(), previous)
        self.assertEqual((self.target / "MANIFEST.json").read_bytes(), previous_manifest)

    def test_one_command_diagnostic_captures_local_report_without_upload(self):
        self.run_script("install.sh")
        program = "import os; print('diagnostic-command-ran'); print('trace='+str(os.getenv('GFG_NATIVE_TRACE')))"
        result = subprocess.run([str(self.launcher), "--diagnose", shutil.which("python3"), "-c", program],
                                env=self.env, text=True, capture_output=True, check=True)
        self.assertIn("diagnostic-command-ran", result.stdout)
        self.assertIn("trace=1", result.stdout)
        captures = list((self.home / ".local/state/gfg-native/diagnostics").glob("*.tar.gz"))
        self.assertEqual(len(captures), 1)
        report = (captures[0].parent / captures[0].name.removesuffix(".tar.gz") / "report.md").read_text()
        self.assertIn("NOT ACCEPTANCE", report)
        self.assertIn("Physical display / KMS scanout: **unobserved**", report)
        self.assertTrue((captures[0].parent / captures[0].name.removesuffix(".tar.gz") / "app.stderr.log").is_file())
        system = (captures[0].parent / captures[0].name.removesuffix(".tar.gz") / "system-start.txt").read_text()
        self.assertIn(hashlib.sha256((self.target / "libVkLayer_gfg_native.so").read_bytes()).hexdigest(), system)

    def test_first_install_rollback_and_uninstall_leave_working_launch_option(self):
        for cleanup in ("rollback.sh", "uninstall.sh"):
            self.run_script("install.sh")
            self.run_script(cleanup)
            self.assertFalse((self.target / "libVkLayer_gfg_native.so").exists())
            self.assertFalse((self.target / "VkLayer_gfg_native.json").exists())
            self.assertFalse((self.target / "diagnose.sh").exists())
            self.assertFalse((self.target / "accept_report.py").exists())
            self.assertEqual(self.launch("/usr/bin/printf", "%s", "a b"), "a b")
            self.assertEqual(self.launch("--off", "/usr/bin/printf", "%s", "a b"), "a b")

    def test_disabled_diagnostic_runs_game_and_preserves_failure_status(self):
        self.run_script("install.sh")
        program = "import os,sys; print('baseline-command-ran'); print('bridge='+str(os.getenv('GFG_NATIVE_GPU_BRIDGE'))); sys.exit(7)"
        result = subprocess.run(
            [str(self.launcher), "--off", "--diagnose", shutil.which("python3"), "-c", program],
            env=self.env, text=True, capture_output=True)
        self.assertEqual(result.returncode, 7)
        self.assertIn("baseline-command-ran", result.stdout)
        self.assertIn("bridge=None", result.stdout)
        captures = list((self.home / ".local/state/gfg-native/diagnostics").glob("*.tar.gz"))
        self.assertEqual(len(captures), 1)
        run = captures[0].parent / captures[0].name.removesuffix(".tar.gz")
        self.assertEqual((run / "process-status.txt").read_text().strip(), "7")
        self.assertIn("mode=passthrough", (run / "system-start.txt").read_text())
        self.assertIn("baseline-command-ran", (run / "app.stdout.log").read_text())


if __name__ == "__main__":
    unittest.main()
