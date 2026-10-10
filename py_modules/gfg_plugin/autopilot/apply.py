"""Apply one scheduler request through the existing power actuator.

The scheduler decides. This module only writes a cap the actuator already owns,
never above its verified ceiling, and restores on a failed ack. It does not
claim power, edit Saved, or touch flow.
"""
from .experiments import ExperimentConfig, Scheduler
from .policy import Knob


class ScheduledPower:
    STEP_W = 1.0
    ACK_W = 0.5

    def __init__(self, power, scheduler=None):
        self._power = power
        self.scheduler = scheduler or Scheduler(ExperimentConfig())
        self.requested = None
        self.baseline_w = None
        self.baseline_fast_w = None
        self.rollback_due = False
        self._slot = None

    @property
    def power(self):
        return self._power() if callable(self._power) else self._power

    def step(self, *, now, seq, real, output, context, ceiling_w, owned, allow, other_busy=False,
             slot=None, restore_pending=False, evidence=True):
        if self.rollback_due:
            return self._restore("baseline-restore-failed", slot, now)
        if restore_pending or self.scheduler.restore_pending:
            if self.scheduler.busy:
                return self._restore("restore-pending", slot, now)
            self._release(slot, "restore-pending")
            return self._idle("restore-pending", "RESTORE")
        self._slot = slot
        if other_busy or self._slot_taken(slot):
            return self._idle("other-tool-busy")
        if self.scheduler.busy and context != self.scheduler.context:
            return self._restore("scene-or-context-changed", slot, now)
        if not allow:
            if self.scheduler.busy:
                return self._restore("trial-withdrawn", slot, now)
            return self._idle("not-a-power-trial")
        if owned is not True:
            if self.scheduler.busy:
                return self._restore("external-ownership", slot, now)
            return self._idle("power-not-owned")
        ceiling = _watts(ceiling_w)
        if ceiling is None:
            return self._idle("ceiling-missing")
        if not self.scheduler.busy:
            if not evidence:
                return self._idle("stale-sample")
            current = _watts((self.power.status() or {}).get("observed_tdp_w"))
            if current is None or current + self.STEP_W > ceiling + 1e-9:
                return self._idle("already-at-ceiling")
            # No predicted FPS is invented. None means a measurement, not a claimed gain.
            error = self.scheduler.start(Knob.POWER_CAP, now, context, expected_gain=None)
            if error:
                return self._idle(error)
            if slot is not None:
                refused = slot.start(Knob.POWER_CAP, now)
                if refused:
                    self.scheduler.cancel(refused)
                    return self._idle(refused)
        if not evidence:
            signal = self.scheduler.observe_clock(now)
        else:
            signal = self.scheduler.observe(seq, now, real, output, None, context)
        if signal == "apply":
            return self._apply(ceiling, now)
        if signal in ("restore", "ack-missing", "delivery-dropped", "scene-or-context-changed") or self.scheduler.needs_restore:
            return self._restore(signal or "restore", slot, now)
        if self.scheduler.phase == "verdict":
            self._release(slot, "verdict")
        return self._idle(signal or self.scheduler.phase, "TRIAL" if self.scheduler.busy else "HOLD", armed=self.scheduler.busy)

    def _apply(self, ceiling, now):
        status = self.power.status()
        current = _watts(status.get("observed_tdp_w"))
        if current is None:
            return self._restore("readback-missing")
        target = min(ceiling, current + self.STEP_W)
        if target > ceiling or target <= current:
            return self._restore("ceiling-blocks-step")
        self.baseline_w = current
        self.baseline_fast_w = _watts(status.get("observed_fast_w"))
        result = self.power.set_tdp_w(target)
        self.requested = target
        state = result.get("state") if isinstance(result, dict) else None
        observed = _watts((state or {}).get("observed_tdp_w"))
        matched = isinstance(result, dict) and result.get("success") is True and observed is not None \
            and abs(observed - target) <= self.ACK_W and observed <= ceiling + self.ACK_W
        self.scheduler.ack(now, matched)
        if not matched:
            return self._restore("power-ack-missing", self._slot, now)
        return {"wrote": True, "armed": True, "action": "TRIAL", "reason": "ack",
                "requested_w": target, "observed_w": observed}

    def _restore(self, reason, slot=None, now=None):
        slot = self._slot if slot is None else slot
        if self.baseline_w is None:
            if self.scheduler.busy:
                self.scheduler.cancel(reason)
            self._release(slot, reason)
            return self._idle(reason, "RESTORE" if self.scheduler.restore_pending else "HOLD")
        result = self.power.set_tdp_w(self.baseline_w)
        state = result.get("state") if isinstance(result, dict) else None
        observed = _watts((state or {}).get("observed_tdp_w"))
        observed_fast = _watts((state or {}).get("observed_fast_w"))
        fast_ok = self.baseline_fast_w is None or (
            observed_fast is not None and abs(observed_fast - self.baseline_fast_w) <= self.ACK_W)
        matched = isinstance(result, dict) and result.get("success") is True and observed is not None \
            and abs(observed - self.baseline_w) <= self.ACK_W and fast_ok
        if matched and self.scheduler._awaiting == "restore-ack" and now is not None:
            self.scheduler.ack(now, True)
            self.rollback_due = False
            self.baseline_w = None
            self.baseline_fast_w = None
        elif matched:
            self.scheduler.restored(True)
            self.rollback_due = False
            self.baseline_w = None
            self.baseline_fast_w = None
        else:
            self.rollback_due = True
            self.scheduler.restored(False)
        self.requested = None
        if self.scheduler.phase == "verdict" or not self.scheduler.busy:
            self._release(slot, reason)
        return {"wrote": False, "armed": self.scheduler.busy, "action": "TRIAL" if self.scheduler.busy else "HOLD",
                "reason": reason if matched else "baseline-restore-failed", "restore_failed": not matched}

    def _slot_taken(self, slot):
        return slot is not None and slot.busy and slot.knob is not Knob.POWER_CAP

    def _release(self, slot, reason):
        if slot is not None and slot.busy and slot.knob is Knob.POWER_CAP:
            slot.abort(reason)

    def _idle(self, reason, action="HOLD", armed=False):
        return {"wrote": False, "armed": armed, "action": action, "reason": reason}


def _watts(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value) if value > 0 else None
