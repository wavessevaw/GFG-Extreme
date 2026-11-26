"""Exercise the historical sandbox source guard, including silent weakening."""
import contextlib
import importlib.util
import io
from pathlib import Path
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("sandbox_source_guard", ROOT / "tools/guard_sandbox_source.py")
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)
BASELINE = (ROOT / "docs/baseline-3.2.2/sandbox-run.py.txt").read_bytes()


class SandboxSourceGuardTest(unittest.TestCase):
    def test_identical_source_is_unverified_not_pass(self):
        result = guard.compare(BASELINE, BASELINE)
        self.assertEqual(result["baseline_scenarios"], 39)
        self.assertEqual(result["status"], "UNVERIFIED")

    def test_changed_predicate_with_same_check_name_is_blocked(self):
        old = b'q["tdp_final"] == 15.0'
        self.assertIn(old, BASELINE)
        candidate = BASELINE.replace(old, b'q["tdp_final"] <= 15.0', 1)
        result = guard.compare(BASELINE, candidate)
        self.assertEqual(result["changed_scenarios"], ["objectives_light_game"])
        self.assertEqual(result["status"], "BLOCKED")

    def test_changed_common_helper_is_blocked(self):
        old = b'0.95 * r["cap"]'
        self.assertIn(old, BASELINE)
        candidate = BASELINE.replace(old, b'0.85 * r["cap"]', 1)
        result = guard.compare(BASELINE, candidate)
        self.assertEqual(result["changed_helpers"], ["metrics"])
        self.assertEqual(result["status"], "BLOCKED")

    def test_removed_scenario_and_duplicate_names_are_not_hidden(self):
        old = b"@scenario\ndef battery_drains_autopilot("
        self.assertIn(old, BASELINE)
        candidate = BASELINE.replace(old, b"def battery_drains_autopilot(", 1)
        self.assertEqual(guard.compare(BASELINE, candidate)["missing_scenarios"], ["battery_drains_autopilot"])
        candidate = BASELINE + b"\n@scenario\ndef battery_drains_autopilot():\n    pass\n"
        with self.assertRaisesRegex(ValueError, "duplicate scenario"):
            guard.compare(BASELINE, candidate)

    def test_extra_scenario_and_comments_do_not_modify_original_contracts(self):
        candidate = b"# Added comment\n" + BASELINE + b"\n@scenario\ndef additional_test():\n    pass\n"
        result = guard.compare(BASELINE, candidate)
        self.assertEqual(result["added_scenarios"], ["additional_test"])
        self.assertEqual(result["status"], "UNVERIFIED")

    def test_altered_historical_source_is_rejected(self):
        with patch.object(guard.Path, "read_bytes", return_value=BASELINE + b"\n"), \
             patch("sys.argv", ["guard", "baseline", "candidate"]), \
             contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as failure:
                guard.main()
        self.assertEqual(failure.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
