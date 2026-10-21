import unittest

import helpers  # noqa: F401

from sandbox import run


class SandboxTest(unittest.TestCase):
    """Every virtual-Deck scenario must pass (model results; see docs/SANDBOX_REPORT.md)."""

    def test_all_scenarios(self):
        results = run.run_all()
        failed = {n: [c for c in r["checks"] if not c["ok"]] for n, r in results.items() if not r["pass"]}
        self.assertEqual(failed, {})
        self.assertGreaterEqual(len(results), 20)


if __name__ == "__main__":
    unittest.main()
