"""One experiment slot. A second tool cannot run until this one is finished."""
from .policy import Knob


DRIFT_RATIO = 0.10
_PHASES = ("prepare", "baseline-a1", "apply", "ack", "settle", "test-b",
           "restore-a", "baseline-a2", "verdict")


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
