"""One experiment slot for the section 4 protocol.

PREPARE → A1 → APPLY → ACK → SETTLE → B → RESTORE → ACK → SETTLE → A2 → VERDICT.
The scheduler records evidence. It does not write an actuator or a memory file.
"""
from dataclasses import dataclass, field
from typing import Optional

from .policy import Knob


DRIFT_RATIO = 0.10
_PHASES = ("prepare", "baseline-a1", "apply", "ack", "settle", "test-b",
           "restore-a", "baseline-a2", "verdict")


def _measurement(real, output, temp, now, seq):
    from .contracts import number
    if number(now) is None or number(seq) is None or number(real) is None or number(output) is None:
        return False
    return temp is None or number(temp) is not None


def _drift(left, right):
    for key in ("output", "real"):
        a, b = left.get(key), right.get(key)
        if a is None or b is None:
            return True
        if abs(a - b) > max(1.0, DRIFT_RATIO * max(a, b)):
            return True
    return False


class SingleFlight:
    def __init__(self):
        self.phase = "idle"
        self.knob = None
        self.windows = {}
        self.verdict = None
        self.reason = ""

    @property
    def busy(self):
        return self.phase not in ("idle", "verdict")

    def start(self, knob, now):
        if knob not in (Knob.POWER_CAP, Knob.FLOW_SCALE):
            return "knob-not-in-c2-pair"
        if self.busy:
            return "slot-busy"
        self.phase = "prepare"
        self.knob = knob
        self.windows = {}
        self.verdict = None
        self.reason = ""
        self.started = now
        return None

    def abort(self, reason):
        self.phase = "idle"
        self.knob = None
        self.windows = {}
        self.verdict = "ABORTED"
        self.reason = reason

    def record(self, phase, metrics):
        if phase not in _PHASES or not self.busy:
            return "no-open-trial"
        self.phase = phase
        if phase in ("baseline-a1", "test-b", "baseline-a2"):
            self.windows[phase] = {"output": metrics.get("output"), "real": metrics.get("real")}
        return None

    def judge(self):
        if not self.busy and self.phase != "verdict":
            return "INCONCLUSIVE"
        first, treatment, second = (self.windows.get(name) for name in ("baseline-a1", "test-b", "baseline-a2"))
        if not first or not treatment or not second:
            self.verdict, self.reason = "INCONCLUSIVE", "incomplete-windows"
        elif _drift(first, second):
            self.verdict, self.reason = "INCONCLUSIVE", "control-window-drift"
        elif treatment.get("output") is None or treatment["output"] < 0.97 * min(first["output"], second["output"]):
            self.verdict, self.reason = "REJECT", "delivery-regression"
        else:
            self.verdict, self.reason = "REJECT", "no-useful-benefit"
        self.phase = "verdict"
        return self.verdict


@dataclass(frozen=True)
class ExperimentConfig:
    min_samples: int = 5
    min_span_s: float = 6.0
    ack_s: float = 15.0
    settle_s: float = 3.0
    max_trials: int = 1
    min_expected_gain: float = 2.0
    temp_drift_c: float = 3.0
    starvation_ratio: float = 0.85


@dataclass(frozen=True)
class TrialResult:
    verdict: str
    baseline_a1: Optional[dict]
    treatment_b: Optional[dict]
    baseline_a2: Optional[dict]
    sample_counts: tuple
    confidence: Optional[float]
    observed_metrics: dict
    invalidation_reason: str
    learned: bool = False
    next_action: str = "HOLD"


@dataclass
class _Window:
    samples: list = field(default_factory=list)

    def add(self, sample, config):
        if self.samples and sample[0] <= self.samples[-1][0]:
            return False
        if self.samples and sample[1] <= self.samples[-1][1]:
            return False
        self.samples.append(sample)
        return True

    def ready(self, config):
        if len(self.samples) < config.min_samples:
            return False
        return self.samples[-1][1] - self.samples[0][1] >= config.min_span_s

    def summary(self):
        return {
            "real": min(sample[2] for sample in self.samples),
            "output": min(sample[3] for sample in self.samples),
            "temp": None if any(sample[4] is None for sample in self.samples) else max(sample[4] for sample in self.samples),
            "n": len(self.samples),
            "seqs": tuple(sample[0] for sample in self.samples),
        }


class Scheduler:
    """Single-flight evidence machine. Callers apply and restore elsewhere."""

    def __init__(self, config=ExperimentConfig()):
        self.config = config
        self.phase = "idle"
        self.knob = None
        self.context = None
        self.restore_pending = False
        self.needs_restore = False
        self.used = {}
        self._windows = {}
        self._awaiting = None
        self._deadline = None
        self._floor = None
        self.result = None
        self._claims = False

    @property
    def busy(self):
        return self.phase not in ("idle", "verdict")

    def start(self, knob, now, context, expected_gain):
        if self.restore_pending or self.needs_restore:
            return "restore-pending"
        if self.busy:
            return "slot-busy"
        if expected_gain is None:
            claimed = False
        elif expected_gain < self.config.min_expected_gain:
            return "expected-gain-too-small"
        else:
            claimed = True
        if self.used.get(context, 0) >= self.config.max_trials:
            return "trial-budget-spent"
        self.phase = "baseline-a1"
        self.knob = knob
        self.context = context
        self.used[context] = self.used.get(context, 0) + 1
        self._windows = {"baseline-a1": _Window()}
        self._awaiting = None
        self._deadline = None
        self._floor = None
        self.needs_restore = False
        self.result = None
        self._claims = claimed
        self._opened = now
        return None

    def observe(self, seq, now, real, output, temp, context):
        if not self.busy:
            return None
        if not _measurement(real, output, temp, now, seq):
            if self.phase == "baseline-a1":
                self._close("ABORTED", "measurement-unavailable")
                return "measurement-unavailable"
            return self._invalidate("measurement-unavailable")
        if context != self.context:
            return self._invalidate("scene-or-context-changed")
        if self._floor is not None and output < self._floor * self.config.starvation_ratio:
            return self._invalidate("delivery-dropped")
        if self._deadline is not None and now > self._deadline:
            return self._invalidate("ack-missing")
        if self.phase in ("apply", "ack", "restore-a", "ack-restore"):
            return None
        if self.phase in ("settle", "settle-a2"):
            if now < self._settle_until:
                return None
            self.phase = "test-b" if self.phase == "settle" else "baseline-a2"
            self._windows[self.phase] = _Window()
        window = self._windows.get(self.phase)
        if window is None or not window.add((seq, now, real, output, temp), self.config):
            return None
        if not window.ready(self.config):
            return None
        summary = window.summary()
        if self._overlaps(summary["seqs"]):
            return self._invalidate("overlapping-samples")
        if self.phase == "baseline-a1":
            self._floor = summary["output"]
            self.phase = "apply"
            self._awaiting = "apply-ack"
            self._deadline = now + self.config.ack_s
            return "apply"
        if self.phase == "test-b":
            self.phase = "restore-a"
            self.needs_restore = True
            self._awaiting = "restore-ack"
            self._deadline = now + self.config.ack_s
            return "restore"
        if self.phase == "baseline-a2":
            return self._judge()
        return None

    def ack(self, now, matched):
        if self._awaiting is None:
            return None
        if self._deadline is not None and now > self._deadline:
            return self._invalidate("ack-missing")
        if not matched:
            return None
        self._deadline = None
        self._awaiting = None
        self.phase = "settle" if self.phase == "apply" else "settle-a2"
        self._settle_until = now + self.config.settle_s
        if self.phase == "settle-a2":
            self.needs_restore = False
        return self.phase

    def observe_clock(self, now):
        """Advance deadlines without counting a repeated or stale renderer receipt."""
        if not self.busy:
            return None
        if self._deadline is not None and now > self._deadline:
            return self._invalidate("ack-missing")
        if self.phase in ("settle", "settle-a2"):
            if now < self._settle_until:
                return None
            self.phase = "test-b" if self.phase == "settle" else "baseline-a2"
            self._windows[self.phase] = _Window()
        return None

    def restored(self, ok):
        if ok:
            self.needs_restore = False
            self.restore_pending = False
            return None
        self.restore_pending = True
        self.needs_restore = True
        self._close("ABORTED", "restore-failed")
        return "restore-pending"

    def cancel(self, reason):
        """Drop a trial that never wrote. It must not block the next one."""
        if self.context in self.used:
            self.used[self.context] = max(0, self.used[self.context] - 1)
        self.phase = "idle"
        self.knob = None
        self.needs_restore = False
        self._claims = False
        self.result = TrialResult("ABORTED", None, None, None, (), None, {"reason": reason}, reason)
        return reason

    def crash(self, reason):
        self.needs_restore = True
        self.restore_pending = True
        return self._close("ABORTED", reason)

    def _overlaps(self, seqs):
        earlier = []
        for name, window in self._windows.items():
            if name == self.phase:
                continue
            earlier.extend(sample[0] for sample in window.samples)
        return any(seq in earlier for seq in seqs)

    def _invalidate(self, reason):
        applied = self.phase not in ("idle", "baseline-a1")
        self.needs_restore = applied
        if applied:
            self.restore_pending = True
        verdict = "INCONCLUSIVE" if reason in ("scene-or-context-changed", "control-window-drift", "temperature-drift") else "ABORTED"
        self._close(verdict, reason)
        return reason

    def _judge(self):
        first = self._windows["baseline-a1"].summary()
        treatment = self._windows["test-b"].summary()
        second = self._windows["baseline-a2"].summary()
        if _drift(first, second):
            self.needs_restore = True
            self._close("INCONCLUSIVE", "control-window-drift", first, treatment, second)
            return "control-window-drift"
        if first["temp"] is not None and second["temp"] is not None and abs(first["temp"] - second["temp"]) > self.config.temp_drift_c:
            self.needs_restore = True
            self._close("INCONCLUSIVE", "temperature-drift", first, treatment, second)
            return "temperature-drift"
        floor = min(first["output"], second["output"])
        if treatment["output"] < 0.97 * floor:
            self._close("REJECT", "delivery-regression", first, treatment, second)
            return "delivery-regression"
        gain = treatment["real"] - max(first["real"], second["real"])
        if gain < self.config.min_expected_gain or not self._claims:
            reason = "no-useful-benefit" if self._claims else "benefit-not-claimed"
            self._close("REJECT", reason, first, treatment, second)
            return reason
        self._close("ACCEPT", "benefit-held", first, treatment, second)
        return "benefit-held"

    def _close(self, verdict, reason, first=None, treatment=None, second=None):
        counts = tuple(len(window.samples) for window in self._windows.values())
        self.result = TrialResult(
            verdict, first, treatment, second, counts, None,
            {"reason": reason, "confidence_interval": "not-computed"},
            "" if verdict == "ACCEPT" else reason,
            learned=False, next_action="HOLD",
        )
        self.phase = "verdict"
        self._awaiting = None
        return self.result
