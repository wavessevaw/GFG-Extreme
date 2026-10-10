"""One optimization at a time. A GPU-clock check freezes planned TDP moves."""
from __future__ import annotations


class Arbiter:
    VERIFY_S = 10.0
    COOLDOWN_S = 30.0
    REJECT_S = 120.0

    def __init__(self) -> None:
        self.state = "OBSERVE"
        self.tool = None
        self.reason = ""
        self.baseline = None
        self.since = 0.0
        self.cooldown_until = 0.0
        self.blocked_until: dict = {}

    @property
    def freeze_tdp(self) -> bool:
        return self.tool == "gpu-clock" and self.state in ("VERIFY", "ROLLBACK")

    def admit(self, action: str, now: float) -> str:
        if self.freeze_tdp:
            return "busy"
        if action in ("HOLD", "PAUSE", "OPTIMIZE_POWER"):
            return "ok"
        if now < self.cooldown_until:
            return "cooldown"
        if self.blocked_until.get(action, 0) > now:
            return "rejected"
        return "ok"

    def begin(self, tool: str, reason: str, now: float, baseline) -> None:
        self.state = "VERIFY"
        self.tool = tool
        self.reason = reason
        self.since = now
        self.baseline = baseline

    def judge(self, now: float, real, output) -> str | None:
        if self.state != "VERIFY":
            return None
        if real is None or output is None:
            if now - self.since > self.VERIFY_S:
                self._reject(now, "measurement-lost")
                return "rollback"
            return "wait"
        base_real, base_out = self.baseline or (None, None)
        if base_real and real < base_real * 0.80:
            self._reject(now, "real-fps-dropped")
            return "rollback"
        if now - self.since < self.VERIFY_S:
            return "wait"
        if base_real and real < base_real * 0.97:
            self._reject(now, "no-gain")
            return "rollback"
        if base_out and output < base_out * 0.97:
            self._reject(now, "output-dropped")
            return "rollback"
        self.state = "HOLD"
        self.tool = None
        self.reason = "verified"
        self.cooldown_until = now + self.COOLDOWN_S
        return "accept"

    def finish_rollback(self) -> None:
        self.state = "COOLDOWN"
        self.tool = None

    def note(self, action: str, reason: str) -> None:
        if self.freeze_tdp:
            return
        self.reason = reason
        self.state = {"PAUSE": "PAUSED", "HOLD": "HOLD", "OPTIMIZE_POWER": "APPLY"}.get(action, "DECIDE")
        if action == "OPTIMIZE_POWER":
            self.tool = "budget"

    def _reject(self, now: float, reason: str) -> None:
        self.blocked_until["OPTIMIZE_GPU_CLOCK"] = now + self.REJECT_S
        self.state = "ROLLBACK"
        self.reason = reason
        self.cooldown_until = now + self.COOLDOWN_S
