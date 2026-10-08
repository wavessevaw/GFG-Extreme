"""Quality transition safety: never wait 25 s on an applied, visibly starved ratio."""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "py_modules")]

from gfg_plugin.governor_confirmation import Request, evaluate_confirmation
from gfg_plugin.governor_core import OperatingPoint


class StubObserver:
    session_generation = 1

    def __init__(self, *, applied=True, output=30.0, mult=1.0):
        self.applied = applied
        self.output = output
        self.mult = mult

    def application_events_after(self, mark):
        if not self.applied:
            return []
        return [SimpleNamespace(operation="runtime-state-applied", event_seq=3)]

    def samples_after_event(self, mark):
        return [SimpleNamespace(monotonic=float(i), event_seq=4 + i,
                                output_fps=self.output, real_fps=30.0,
                                effective_multiplier=self.mult)
                for i in range(10)]


class QualityConfirmationTests(unittest.TestCase):
    def request(self):
        return Request(request_id=1, point=OperatingPoint("72x1.25", 90, 72, 1.25, 100),
                       deltas={}, previous_deltas={}, revision=2, created=0.0,
                       event_mark=1, generation=1, external=False)

    def decide(self, observer, *, fast=True):
        return evaluate_confirmation(self.request(), observer, 9.0, budget=True,
                                     min_samples=8, min_span_s=4.0,
                                     timeout_s=25.0, early_span_s=8.0,
                                     fast_mismatch=fast)

    def test_applied_quality_point_with_30_output_fails_early(self):
        self.assertEqual(self.decide(StubObserver()),
                         ("failed", "applied-ratio-not-delivering"))

    def test_no_applied_event_does_not_guess_a_failure(self):
        self.assertEqual(self.decide(StubObserver(applied=False))[0], "wait")

    def test_no_fast_reject_when_output_is_healthy(self):
        self.assertEqual(self.decide(StubObserver(output=90.0))[0], "wait")

    def test_budget_mode_unchanged_by_default(self):
        self.assertEqual(self.decide(StubObserver(), fast=False)[0], "wait")

    def test_requested_ratio_does_not_trigger_mismatch_guard(self):
        self.assertEqual(self.decide(StubObserver(mult=1.25))[0], "confirmed")


if __name__ == "__main__":
    unittest.main()
