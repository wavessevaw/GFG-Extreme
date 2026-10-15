"""Evidence-packet boundaries: no closed payloads, precise plans, bounded tools."""
import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

spec = importlib.util.spec_from_file_location("native_fg_probe", Path(__file__).resolve().parents[1] / "tools/native_fg_probe.py")
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


class NativeProbeTests(unittest.TestCase):
    def test_multiframe_positions(self):
        for multiplier in (2, 3, 5):
            plan = probe.quality_plan(multiplier).split(";")
            self.assertEqual(len(plan), 12)
            self.assertEqual(plan[:10], ["history"] * 10)
            points = list(map(float, plan[10].split(",")))
            self.assertEqual(len(points), multiplier - 1)
            for i, point in enumerate(points, 1):
                self.assertAlmostEqual(point, i / multiplier, places=8)

    def test_packet_excludes_closed_payloads_and_symlinks(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "evidence"
            root.mkdir()
            for name in ("Lossless.dll", "weights.bin", "shader.spv", "secret.exe"):
                (root / name).write_bytes(b"private")
            (root / "report.json").write_text("{}")
            (root / "stolen.txt").symlink_to(root / "Lossless.dll")
            out = Path(temp) / "packet.zip"
            probe.pack(root, out)
            with zipfile.ZipFile(out) as z:
                self.assertEqual(z.namelist(), ["report.json"])
            with self.assertRaises(FileExistsError):
                probe.pack(root, out)

    def test_timed_out_tool_is_not_success(self):
        result = probe.run_command([sys.executable, "-c", "import time; time.sleep(30)"], timeout=0.05)
        self.assertEqual(result["status"], "TIMEOUT")
        self.assertNotEqual(result["returncode"], 0)

    def test_missing_dependency_is_recorded(self):
        self.assertEqual(probe.run_command(["/no-such-gfg-command"])["status"], "UNAVAILABLE")

    def test_reference_environment_overrides_inherited_backend(self):
        old = os.environ.get("GFG_TEMPORAL_ENGINE")
        try:
            os.environ["GFG_TEMPORAL_ENGINE"] = "experimental"
            result = probe.run_command([sys.executable, "-c",
                "import os; print(os.environ['GFG_TEMPORAL_ENGINE'])"],
                env_overrides={"GFG_TEMPORAL_ENGINE": "off"})
            self.assertEqual(result["stdout"].strip(), "off")
            self.assertEqual(os.environ["GFG_TEMPORAL_ENGINE"], "experimental")
        finally:
            if old is None:
                os.environ.pop("GFG_TEMPORAL_ENGINE", None)
            else:
                os.environ["GFG_TEMPORAL_ENGINE"] = old

    def test_home_and_model_paths_are_redacted(self):
        self.assertEqual(probe.redact("/models/Lossless.dll", ["/models/Lossless.dll"]), "<private-path>")

    def test_nonexistent_device_fields_stay_unknown(self):
        with tempfile.TemporaryDirectory() as root:
            result = probe.device_inventory(Path(root))
            self.assertIsNone(result["model"])
            self.assertEqual(result["gpus"], [])


if __name__ == "__main__":
    unittest.main()
