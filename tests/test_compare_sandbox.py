import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("compare_sandbox", Path(__file__).resolve().parents[1] / "tools" / "compare_sandbox.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def run(*checks):
    return {"scene": {"checks": [{"name": name, "ok": ok} for name, ok in checks],
                      "pass": all(ok for _, ok in checks)}}


class CompareSandboxTest(unittest.TestCase):
    def test_missing_and_failed_checks_block(self):
        result = module.compare(run(("a", True), ("b", True)), run(("a", False)))
        self.assertEqual(result["missing_checks"], {"scene": ["b"]})
        self.assertEqual(result["failed_checks"], {"scene": ["a"]})
        self.assertEqual(result["status"], "BLOCKED")

    def test_identical_checks_are_only_unverified(self):
        self.assertEqual(module.compare(run(("a", True)), run(("a", True)))["status"], "UNVERIFIED")

    def test_failed_reference_is_blocked(self):
        self.assertEqual(module.compare(run(("a", False)), run(("a", True)))["status"], "BLOCKED")

    def test_numeric_changes_are_observations_not_pass(self):
        before, after = run(("a", True)), run(("a", True))
        before["scene"]["metrics"] = {"energy_wh": 2.0, "enabled": True}
        after["scene"]["metrics"] = {"energy_wh": 1.5, "enabled": False}
        result = module.compare(before, after)
        self.assertEqual(result["observed_numeric_changes"], {
            "scene": {"/metrics/energy_wh": {"reference": 2.0, "target": 1.5, "delta": -0.5}}})
        self.assertEqual(result["status"], "UNVERIFIED")

    def test_missing_values_are_not_treated_as_zero(self):
        before, after = run(("a", True)), run(("a", True))
        before["scene"]["metrics"] = {"fps": 30}
        after["scene"]["metrics"] = {"energy": 2}
        result = module.compare(before, after)
        self.assertEqual(result["missing_numeric"], {"scene": ["/metrics/fps"]})
        self.assertEqual(result["added_numeric"], {"scene": ["/metrics/energy"]})
        self.assertEqual(result["observed_numeric_changes"], {})
        self.assertEqual(result["status"], "UNVERIFIED")

    def test_input_hash_identifies_exact_bytes(self):
        with patch.object(module.Path, "read_bytes", return_value=b"{}"):
            result, digest = module.load_result("unused.json")
        self.assertEqual(result, {})
        self.assertEqual(digest, "44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a")

    def test_empty_duplicate_and_inconsistent_results_rejected(self):
        for value in ({}, run(("a", True), ("a", True)),
                      {"scene": {"checks": [{"name": "a", "ok": True}], "pass": False}}):
            with self.subTest(value=value), self.assertRaises(ValueError):
                module.checks(value)


if __name__ == "__main__":
    unittest.main()
