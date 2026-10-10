"""Apply one scheduler request through the existing power actuator.

The scheduler decides. This module only writes a cap the actuator already owns,
never above its verified ceiling, and restores on a failed ack. It does not
claim power, edit Saved, or touch flow.
"""
from .experiments import ExperimentConfig, Scheduler
from .policy import Knob
from ..governor_restore import power_restore_error


class ScheduledPower:
    STEP_W = 1.0
    ACK_W = 0.5

    def __init__(self, power, scheduler=None):
        self._power = power
        self.scheduler = scheduler or Scheduler(ExperimentConfig())
        self.requested = None

    @property
    def power(self):
        return self._power() if callable(self._power) else self._power

    def step(self, *, now, seq, real, output, context, ceiling_w, owned, allow, other_busy=False):
        if other_busy:
            return self._idle("other-tool-busy")
        if self.scheduler.restore_pending:
            return self._idle("restore-pending", "RESTORE")
        if not allow:
            if self.scheduler.busy:
                return self._restore("trial-withdrawn")
            return self._idle("not-a-power-trial")
        if owned is not True:
            if self.scheduler.busy:
                return self._restore("external-ownership")
            return self._idle("power-not-owned")
        ceiling = _watts(ceiling_w)
        if ceiling is None:
            return self._idle("ceiling-missing")
        if not self.scheduler.busy:
            current = _watts((self.power.status() or {}).get("observed_tdp_w"))
            if current is None or current + self.STEP_W > ceiling + 1e-9:
                return self._idle("already-at-ceiling")
            error = self.scheduler.start(Knob.POWER_CAP, now, context, expected_gain=self.scheduler.config.min_expected_gain)
            if error:
                return self._idle(error)
        signal = self.scheduler.observe(seq, now, real, output, None, context)
        if signal == "apply":
            return self._apply(ceiling, now)
        if signal in ("restore", "ack-missing", "delivery-dropped", "scene-or-context-changed") or self.scheduler.needs_restore:
            return self._restore(signal or "restore")
        return self._idle(signal or self.scheduler.phase, "TRIAL" if self.scheduler.busy else "HOLD", armed=self.scheduler.busy)

    def _apply(self, ceiling, now):
        status = self.power.status()
        current = _watts(status.get("observed_tdp_w"))
        if current is None:
            return self._restore("readback-missing")
        target = min(ceiling, current + self.STEP_W)
        if target > ceiling or target <= current:
            return self._restore("ceiling-blocks-step")
        result = self.power.set_tdp_w(target)
        self.requested = target
        state = result.get("state") if isinstance(result, dict) else None
        observed = _watts((state or {}).get("observed_tdp_w"))
        matched = isinstance(result, dict) and result.get("success") is True and observed is not None \
            and abs(observed - target) <= self.ACK_W and observed <= ceiling + self.ACK_W
        self.scheduler.ack(now, matched)
        if not matched:
            return self._restore("power-ack-missing")
        return {"wrote": True, "armed": True, "action": "TRIAL", "reason": "ack",
                "requested_w": target, "observed_w": observed}

    def _restore(self, reason):
        error = power_restore_error(self.power.restore_if_owned())
        self.scheduler.restored(error is None)
        self.requested = None
        return {"wrote": False, "armed": False, "action": "RESTORE" if error else "HOLD",
                "reason": error or reason, "restore_failed": error is not None}

    def _idle(self, reason, action="HOLD", armed=False):
        return {"wrote": False, "armed": armed, "action": action, "reason": reason}


def _watts(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value) if value > 0 else None
