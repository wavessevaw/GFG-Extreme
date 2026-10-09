"""Did the renderer really take an Operating Point?  (Split out of ``governor_service`` in 1.0.4.)

Writing the runtime overlay is not application.  A request counts as applied only after fresh
renderer evidence that postdates the write: a run of FPS samples at the requested multiplier, long
enough to rule out a transient.  Pure functions over a ``TelemetryObserver``; the service owns the
request lifecycle (rollback, events, budget notification).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List

from .governor_core import OperatingPoint, multiplier_tolerance

APPLIED_OPERATIONS = frozenset({"runtime-state-applied", "runtime-transition-applied"})
FAILED_OPERATIONS = frozenset({"runtime-transition-failed"})
EARLY_DELIVERED_SPAN_SECONDS = 8.0


@dataclass
class Request:
    """One pending Operating Point application (own correlation, not sample_seq)."""

    request_id: int
    point: OperatingPoint
    deltas: Dict[str, Any]
    previous_deltas: Dict[str, Any]
    revision: int
    created: float
    event_mark: int
    generation: int
    external: bool
    stage: str = "confirming"  # confirming -> trial
    confirmation_mode: str = ""
    window_floor_event_seq: int = 0
    confirmed_at: float = 0.0
    created_wall: float = 0.0  # wall clock at the write: renderer files carry unix timestamps

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "point": self.point.key,
            "stage": self.stage,
            "revision": self.revision,
            "event_mark": self.event_mark,
            "confirmation_mode": self.confirmation_mode,
        }


def _at_ratio(req: Request, sample: Any, want: float, tol: float) -> bool:
    return abs(sample.effective_multiplier - want) <= tol or (
        req.point.multiplier == 1 and sample.effective_multiplier <= 1.12
    )


def evaluate_confirmation(
    req: Request, observer: Any, now: float, *, budget: bool,
    min_samples: int, min_span_s: float, timeout_s: float,
    early_span_s: float = EARLY_DELIVERED_SPAN_SECONDS,
    fast_mismatch: bool = False,
) -> tuple[str, str]:
    """Return (wait|confirmed|failed, reason).  On confirmation ``req`` is updated in place."""
    if observer.session_generation != req.generation:
        return "failed", "telemetry-session-changed"
    events = observer.application_events_after(req.event_mark)
    if any(event.operation in FAILED_OPERATIONS for event in events):
        return "failed", "renderer-transition-failed"
    applied = [event for event in events if event.operation in APPLIED_OPERATIONS]
    samples = observer.samples_after_event(applied[-1].event_seq if applied else req.event_mark)
    want = float(req.point.multiplier)
    tol = multiplier_tolerance(want)
    tail = samples[-min_samples:]
    consistent = len(tail) >= min_samples and all(_at_ratio(req, sample, want, tol) for sample in tail)
    if consistent and (tail[-1].monotonic - tail[0].monotonic) >= min_span_s:
        run: list = []
        for sample in reversed(samples):
            if _at_ratio(req, sample, want, tol):
                run.append(sample)
            else:
                break
        req.window_floor_event_seq = run[-1].event_seq - 1
        req.confirmation_mode = "event+cadence" if applied else "cadence-only"
        req.confirmed_at = now
        return "confirmed", req.confirmation_mode
    if budget and delivered_deeper(req, applied, samples, want, tol, min_samples=min_samples, span_s=early_span_s):
        return "failed", "delivered-deeper-ratio"
    # Quality used to wait 25 s for a renderer that *acknowledged* the new
    # overlay but kept the previous low-FPS cadence.  After an applied event and
    # a full, stable observation window, a mismatched ratio AND starved output
    # cannot be confirmation; reject it without repeatedly punishing the player.
    # Never infer this from a missing apply event or stale/mixed samples.
    if fast_mismatch and applied and len(samples) >= min_samples:
        end = samples[-1].monotonic
        recent = [sample for sample in samples if end - sample.monotonic <= early_span_s]
        if (len(recent) >= min_samples
                and recent[-1].monotonic - recent[0].monotonic >= early_span_s * 0.8
                and all(not _at_ratio(req, sample, want, tol)
                        and sample.output_fps < 0.8 * req.point.target_output_fps
                        for sample in recent)):
            return "failed", "applied-ratio-not-delivering"
    if now - req.created > timeout_s:
        return "failed", "confirmation-timeout"
    return "wait", "awaiting-fresh-evidence"


def delivered_deeper(req: Request, applied: List[Any], samples: List[Any], want: float, tol: float, *,
                     min_samples: int, span_s: float = EARLY_DELIVERED_SPAN_SECONDS) -> bool:
    """Battery/Balanced only: the renderer took the request but holds the target with fewer
    real frames (the GPU cannot feed the requested cap).  Seen on a Deck for 40x2.25,
    36x2.5 and 33x2.75: each waited the full 25 s timeout.  Decide after 8 s of fresh,
    consistent samples instead; the budget then follows the delivered point (verifying).
    """
    if not applied or len(samples) < min_samples:
        return False
    end = samples[-1].monotonic
    tail = [sample for sample in samples if end - sample.monotonic <= span_s]
    if len(tail) < min_samples or len(tail) == len(samples) and (end - samples[0].monotonic) < span_s:
        return False  # not yet 8 s of evidence after the renderer applied the request
    target = float(req.point.target_output_fps)
    base = float(req.point.base_target_fps)
    return all(
        sample.effective_multiplier > want + tol
        and sample.output_fps >= 0.94 * target
        and sample.real_fps <= 0.95 * base
        for sample in tail
    )


def matches(point: Dict[str, Any], summary: Dict[str, Any]) -> bool:
    """The running state already *is* this point (adopt it without a request)."""
    latest = summary.get("latest") or {}
    mult = latest.get("effective_multiplier")
    output = (summary.get("output") or {}).get("median")
    p5 = (summary.get("real") or {}).get("p5")
    if not all(isinstance(v, (int, float)) and math.isfinite(float(v)) for v in (mult, output, p5)):
        return False
    return (
        abs(float(mult) - float(point["multiplier"])) <= multiplier_tolerance(point["multiplier"])
        and float(output) >= float(point["target_output_fps"]) * 0.94
        and float(p5) >= float(point["base_target_fps"]) * 1.05
        and int(point["render_scale_pct"]) == 100
    )
