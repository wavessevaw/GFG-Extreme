"""Real shell install/launch/rollback contract for SteamOS GSF (no Vulkan hardware)."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1] / "engine/gfg-native/package"
FILES = ("libVkLayer_gfg_native.so", "VkLayer_gfg_native.json",
         "gfg-native.sh", "diagnose.sh", "accept_report.py", "MANIFEST.json")

class GsfSteamLauncherTest(unittest.TestCase):
    def test_install_launch_guard_isolated_layer_and_rollback(self):
        with tempfile.TemporaryDirectory(prefix="gsf-steamos-") as directory:
            tmp = Path(directory)
            home = tmp / "deck"
            home.mkdir()
            pkg = tmp / "native"
            pkg.mkdir()
            for name in ("install.sh", "rollback.sh", "gfg-native.sh", "diagnose.sh"):
                shutil.copy2(ROOT / name, pkg / name)
            (pkg / "libVkLayer_gfg_native.so").write_bytes(b"ELF fixture")
            (pkg / "VkLayer_gfg_native.json").write_text(
                '{"file_format_version":"1.2.1","layer":{"name":"VK_LAYER_GFG_native",'
                '"library_path":"./libVkLayer_gfg_native.so"}}')
            (pkg / "accept_report.py").write_text("# test only\n")
            (pkg / "MANIFEST.json").write_text('{"kind":"provenance-only"}\n')
            digests = [hashlib.sha256((pkg / name).read_bytes()).hexdigest() + "  " + name
                       for name in FILES]
            (pkg / "SHA256SUMS.txt").write_text("\n".join(digests) + "\n")
            env = dict(os.environ, HOME=str(home), XDG_DATA_HOME=str(home / ".local/share"),
                       XDG_STATE_HOME=str(home / ".local/state"),
                       XDG_CONFIG_HOME=str(home / ".config"))
            def run(argv, expected=0, extra=None):
                result = subprocess.run([str(v) for v in argv], env={**env, **(extra or {})},
                                        capture_output=True, text=True, timeout=15)
                self.assertEqual(result.returncode, expected, (argv, result.stderr))
                return result
            run(("bash", pkg / "install.sh"))
            root = home / ".local/share/gfg-native"
            loader = root / "vulkan-layers"
            self.assertEqual(sorted(p.name for p in loader.iterdir()),
                             ["VkLayer_gfg_native.json", "libVkLayer_gfg_native.so"])
            self.assertEqual((loader / "libVkLayer_gfg_native.so").read_bytes(),
                             b"ELF fixture")
            self.assertTrue((root / "MANIFEST.json").is_file())
            self.assertFalse((loader / "MANIFEST.json").exists())
            launcher = home / ".local/bin/gfg-native"
            code = ("import json,os;"
                    "print(json.dumps({k:os.environ.get(k) for k in "
                    "['VK_LAYER_PATH','VK_INSTANCE_LAYERS','GFG_NATIVE_FG',"
                    "'DISABLE_GFG_NATIVE_FG']}))")
            active = run((launcher, sys.executable, "-c", code),
                         extra={"GFG_NATIVE_MODE": "2"})
            variables = json.loads(active.stdout)
            self.assertEqual(variables["VK_LAYER_PATH"].split(":")[0], str(loader))
            self.assertEqual(variables["VK_INSTANCE_LAYERS"], "VK_LAYER_GFG_native")
            self.assertEqual(variables["GFG_NATIVE_FG"], "1")
            off = run((launcher, "--off", sys.executable, "-c", code),
                      extra={"VK_INSTANCE_LAYERS": "VK_LAYER_GFG_native:VK_LAYER_OTHER",
                             "GFG_NATIVE_FG": "1"})
            bypass = json.loads(off.stdout)
            self.assertEqual(bypass["VK_INSTANCE_LAYERS"], "VK_LAYER_OTHER")
            self.assertIsNone(bypass["GFG_NATIVE_FG"])
            self.assertEqual(bypass["DISABLE_GFG_NATIVE_FG"], "1")
            for mode in ([], ["--off"], ["--diagnose"]):
                failed = run((launcher, *mode, "%command%"), expected=2)
                self.assertIn("did not expand", failed.stderr)
            failed = run(("bash", pkg / "diagnose.sh", "--native", "%command%"),
                         expected=2)
            self.assertIn("literal", failed.stderr)
            # Re-running an already installed package must preserve rollback.
            run(("bash", pkg / "install.sh"))
            run(("bash", pkg / "rollback.sh"))
            self.assertFalse((root / "libVkLayer_gfg_native.so").exists())
            self.assertFalse((loader / "VkLayer_gfg_native.json").exists())
            self.assertFalse((loader / "libVkLayer_gfg_native.so").exists())

if __name__ == "__main__":
    unittest.main()
