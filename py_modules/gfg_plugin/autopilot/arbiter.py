"""One optimization at a time. Planned work waits until a check is confirmed."""
from __future__ import annotations


class Arbiter:
    SETTLE_S = 2.0
    VERIFY_S = 8.0
    COOLDOWN_S = 30.0
    REJECT_S = 120.0

    def __init__(self) -> None:
        self.state = "OBSERVE"
        self.tool = None
        self.reason = ""
        self.baseline = None
        self.since = 0.0
        self.after_seq = 0
        self.cooldown_until = 0.0
        self.blocked_until: dict = {}

    @property
    def freeze_tdp(self) -> bool:
        return self.tool == "gpu-clock" and self.state in ("SETTLE", "VERIFY", "ROLLBACK", "RESTORE_PENDING")

    @property
    def blocks_planned(self) -> bool:
        return self.freeze_tdp or self.state == "RESTORE_PENDING"

    def admit(self, action: str, now: float) -> str:
        if self.blocks_planned:
            return "busy"
        if action in ("HOLD", "PAUSE", "OPTIMIZE_POWER"):
            return "ok"
        if now < self.cooldown_until:
            return "cooldown"
        if self.blocked_until.get(action, 0) > now:
            return "rejected"
        return "ok"

    def begin(self, tool: str, reason: str, now: float, baseline: dict) -> None:
        self.state = "SETTLE"
        self.tool = tool
        self.reason = reason
        self.since = now
        self.baseline = dict(baseline)
        self.after_seq = int(baseline.get("sample_seq") or 0)

    def judge(self, now: float, evidence: dict) -> str | None:
        if self.state not in ("SETTLE", "VERIFY"):
            return None
        if evidence.get("session") != self.baseline.get("session"):
            self._reject(now, "context-changed")
            return "rollback"
        if int(evidence.get("samples") or 0) < 5 or float(evidence.get("span_s") or 0) < 2.0:
            if now - self.since > self.SETTLE_S + self.VERIFY_S + 8:
                self._reject(now, "measurement-lost")
                return "rollback"
            return "wait"
        if int(evidence.get("sample_seq") or 0) <= self.after_seq:
            return "wait"
        if evidence.get("real") is None or evidence.get("output") is None:
            if now - self.since > self.SETTLE_S + self.VERIFY_S:
                self._reject(now, "measurement-lost")
                return "rollback"
            return "wait"
        if _collapsed(self.baseline, evidence) or _hot(evidence):
            self._reject(now, "real-fps-dropped" if not _hot(evidence) else "thermal-limited")
            return "rollback"
        if self.state == "SETTLE":
            if now - self.since < self.SETTLE_S:
                return "wait"
            self.state = "VERIFY"
            self.since = now
            self.after_seq = int(evidence.get("sample_seq") or self.after_seq)
            return "wait"
        if now - self.since < self.VERIFY_S:
            return "wait"
        if int(evidence.get("sample_seq") or 0) <= self.after_seq:
            return "wait"
        if _gain(self.baseline, evidence):
            self.state = "HOLD"
            self.tool = None
            self.reason = "verified-gain"
            self.cooldown_until = now + self.COOLDOWN_S
            return "accept"
        self._reject(now, "no-measurable-gain")
        return "rollback"

    def finish_rollback(self) -> None:
        self.state = "COOLDOWN"
        self.tool = None

    def mark_restore_pending(self, reason: str) -> None:
        self.state = "RESTORE_PENDING"
        self.tool = "gpu-clock"
        self.reason = reason

    def note(self, action: str, reason: str) -> None:
        if self.blocks_planned:
            return
        self.reason = reason
        self.state = {"PAUSE": "PAUSED", "HOLD": "HOLD", "OPTIMIZE_POWER": "APPLY"}.get(action, "DECIDE")
        self.tool = "budget" if action == "OPTIMIZE_POWER" else None

    def _reject(self, now: float, reason: str) -> None:
        self.blocked_until["OPTIMIZE_GPU_CLOCK"] = now + self.REJECT_S
        self.state = "ROLLBACK"
        self.tool = "gpu-clock"
        self.reason = reason
        self.cooldown_until = now + self.COOLDOWN_S


def _gain(before: dict, after: dict) -> bool:
    real, out = before.get("real"), before.get("output")
    if not real or not out or after.get("real") is None or after.get("output") is None:
        return False
    if after["output"] < out * 0.97:
        return False
    frame_before, frame_after = before.get("frametime_p95"), after.get("frametime_p95")
    if frame_before and frame_after and frame_after > frame_before * 1.10:
        return False
    if after["real"] >= real * 1.05:
        return True
    draw_before, draw_after = before.get("draw_w"), after.get("draw_w")
    equivalent = after["real"] >= real * 0.98 and after["output"] >= out * 0.98
    return bool(equivalent and draw_before and draw_after and draw_after <= draw_before - 0.5)


def _collapsed(before: dict, after: dict) -> bool:
    real = before.get("real")
    return bool(real and after.get("real") is not None and after["real"] < real * 0.80)


def _hot(evidence: dict) -> bool:
    temp = evidence.get("temp_c")
    return temp is not None and temp >= 90
