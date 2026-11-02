import unittest
import sys

import helpers  # noqa: F401

from sandbox import run
from tools.candidate_scope_gate import EXCEPTION
from tools.compare_sandbox import checks


class SandboxTest(unittest.TestCase):
    """Run every scenario; enforce the explicit owner-approved LCD60 scope."""

    def test_all_scenarios_under_owner_approved_scope(self):
        results = run.run_all()
        checks(results)  # Reject empty/malformed/inconsistent results, including the exception.
        failed = {n: [c for c in r["checks"] if not c["ok"]] for n, r in results.items() if not r["pass"]}
        # Original all-PASS requirement is retained in history. Only this exact
        # 75 Hz assertion is outside admission, per CANDIDATE_LCD60_SCOPE.md.
        unexpected = {n: [c for c in entries if (n, c["name"]) != EXCEPTION]
                      for n, entries in failed.items()}
        self.assertEqual({n: entries for n, entries in unexpected.items() if entries}, {})
        if failed:
            print(f"Raw scenario FAIL retained outside candidate scope: {failed}", file=sys.stderr)
        self.assertEqual(set(results), set(run.SCENARIOS))
        self.assertGreaterEqual(len(results), 39)


if __name__ == "__main__":
    unittest.main()
