import importlib.util
from pathlib import Path
import unittest

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

    def test_empty_duplicate_and_inconsistent_results_rejected(self):
        for value in ({}, run(("a", True), ("a", True)),
                      {"scene": {"checks": [{"name": "a", "ok": True}], "pass": False}}):
            with self.subTest(value=value), self.assertRaises(ValueError):
                module.checks(value)


if __name__ == "__main__":
    unittest.main()
