"""One power-cap trial through the existing actuator. No second writer, no Saved edits.

The step is one watt toward the verified ceiling, never past it. A failed write or
readback restores immediately. The winner is not written back: this slice only
checks that the trial can be applied and undone.
"""
from .experiments import SingleFlight
from ..governor_restore import power_restore_error
from .policy import Action, Knob


class PowerTrial:
    STEP_W = 1.0
    ACK_W = 0.5

    def __init__(self, power, slot=None, cooldown_s=30.0):
        self._power = power
        self.slot = slot or SingleFlight()
        self.cooldown_s = cooldown_s
        self.quiet_until = None
        self.requested = None

    @property
    def power(self):
        return self._power() if callable(self._power) else self._power

    def step(self, decision, window, *, now, restore_pending=False):
        if restore_pending or decision.action is Action.RESTORE or decision.release_slot:
            return self._undo("restore-pending", now)
        if decision.action is not Action.TRIAL or decision.knob is not Knob.POWER_CAP:
            if self.slot.busy and self.slot.knob is Knob.POWER_CAP:
                return self._undo("trial-withdrawn", now)
            return self._idle(decision.reason, decision.action.value)
        if self.quiet_until is not None and now < self.quiet_until and not self.slot.busy:
            return self._idle("trial-cooldown", "HOLD")
        if self.slot.phase in ("idle", "verdict", "baseline-a1"):
            status = self.power.status()
            if not isinstance(status, dict) or status.get("owned") is not True:
                return self._undo("power-not-owned", now) if self.slot.busy else self._idle("power-not-owned", "HOLD")
            ceiling, current = _watts(status.get("ceiling_tdp_w")), _watts(status.get("observed_tdp_w"))
            if ceiling is None or current is None:
                return self._undo("ceiling-or-readback-missing", now) if self.slot.busy else self._idle("ceiling-or-readback-missing", "HOLD")
        else:
            ceiling = current = None
        if self.slot.phase in ("idle", "verdict"):
            if current + self.STEP_W > ceiling + 1e-9:
                return self._idle("already-at-ceiling", "HOLD")
            if not _window(window):
                return self._idle("baseline-missing", "OBSERVE")
            error = self.slot.start(Knob.POWER_CAP, now)
            if error:
                return self._idle(error, "HOLD")
            self.slot.record("baseline-a1", window)
            return self._busy("baseline-a1")
        if self.slot.phase == "baseline-a1":
            target = min(ceiling, current + self.STEP_W)
            if target > ceiling or target <= current:
                return self._undo("ceiling-blocks-step", now)
            result = self.power.set_tdp_w(target)
            self.requested = target
            observed = _watts(((result or {}).get("state") or status).get("observed_tdp_w")) if isinstance(result, dict) else None
            if not isinstance(result, dict) or result.get("success") is not True or observed is None \
                    or abs(observed - target) > self.ACK_W or observed > ceiling + self.ACK_W:
                return self._undo("power-ack-missing", now)
            self.slot.record("ack", {})
            return {"wrote": True, "armed": True, "action": "TRIAL", "reason": "ack",
                    "requested_w": target, "observed_w": observed}
        if self.slot.phase == "ack":
            if not _window(window):
                return self._busy("waiting-test-window")
            self.slot.record("test-b", window)
            return self._restore_baseline(now)
        if self.slot.phase == "restore-a":
            if not _window(window):
                return self._busy("waiting-a2")
            self.slot.record("baseline-a2", window)
            verdict = self.slot.judge()
            self.quiet_until = now + self.cooldown_s
            self.requested = None
            return {"wrote": False, "armed": False, "action": "HOLD", "reason": self.slot.reason,
                    "verdict": verdict, "reapplied": False}
        return self._undo("unexpected-phase", now)

    def _restore_baseline(self, now):
        error = power_restore_error(self.power.restore_if_owned())
        if error:
            self.slot.abort(error)
            self.quiet_until = now + self.cooldown_s
            return {"wrote": False, "armed": False, "action": "RESTORE", "reason": error, "restore_failed": True}
        self.slot.record("restore-a", {})
        return self._busy("restored-for-a2")

    def _undo(self, reason, now):
        error = power_restore_error(self.power.restore_if_owned())
        self.slot.abort(error or reason)
        self.quiet_until = now + self.cooldown_s
        self.requested = None
        return {"wrote": False, "armed": False, "action": "RESTORE", "reason": error or reason,
                "restore_failed": error is not None}

    def _busy(self, reason):
        return {"wrote": False, "armed": True, "action": "TRIAL", "reason": reason}

    def _idle(self, reason, action):
        return {"wrote": False, "armed": False, "action": action, "reason": reason}


def _watts(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value) if value > 0 else None


def _window(window):
    return isinstance(window, dict) and isinstance(window.get("output"), (int, float)) \
        and isinstance(window.get("real"), (int, float)) and not isinstance(window.get("output"), bool)
