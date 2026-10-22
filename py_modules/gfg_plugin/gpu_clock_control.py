"""GPU clock ceiling in GFG Extreme 3.0: the 2.x CPU-bound rule on a KEDAVRA point.

When the busiest CPU core is near its limit (>= 85 %) and the GPU is lightly loaded (<= 70 %),
the frame rate is the CPU's, and a GPU clocked higher than it needs only costs watts. The 2.x
autopilot then lowered the GPU clock one 100 MHz step at a time through SteamOSManager's
manual GPU clock (the Quick Access Menu's slider) and kept a step only when it measurably
held the frame rate. Same rule here, with 3.0's discipline:

* only on a locked, engine-confirmed point, Governor settled, not in menus, Power Split idle;
* each step is judged against the window before it: real frames must hold the point and the
  APU draw must drop, or the step is taken back and this game is left alone for a while;
* real frames dipping under the point lift the clock at once (a step back up);
* any change restarts the Governor's and the pilot's windows (``changes``);
* leaving the point, the game or the setting hands the player's clock back.
"""
from __future__ import annotations

import statistics
import time
from collections import deque
from typing import Any, Callable, Deque, Dict, Optional

CPU_BOUND_PCT = 85.0
GPU_LIGHT_PCT = 70.0
OBSERVE_S = 20.0         # CPU-bound this long before the first step
SETTLE_S = 5.0
VERIFY_S = 20.0
HOLD_S = 60.0            # a kept step holds this long before the next one is tried
REJECT_S = 600.0         # after a step that did not pay, this game is left alone
MIN_SAVING_W = 0.3
HOLD_RATIO = 0.98        # real frames must hold the point within 2 %
GUARD_RATIO = 0.93       # under this, the clock goes back up at once
MAX_STEPS = 6
COVERAGE = 0.6           # share of the verify window's seconds with a reading (audit 3.0.0)


class GpuClockControl:
    def __init__(self, gpu: Any, clock: Callable[[], float] = time.monotonic,
                 journal: Optional[Callable[..., None]] = None) -> None:
        self.gpu = gpu
        self.clock = clock
        self.journal = journal
        self.phase = "off"
        self.since = clock()
        self.key: Optional[str] = None
        self.reals: Deque[float] = deque(maxlen=int(VERIFY_S))
        self.draws: Deque[float] = deque(maxlen=int(VERIFY_S))
        self.baseline: Optional[Dict[str, float]] = None
        self.steps = 0
        self.blocked_until = 0.0
        self.changes = 0
        self.changed_at = -1e9
        self.status: Dict[str, Any] = {"phase": "off"}

    def _note(self, kind: str, **fields: Any) -> None:
        if self.journal:
            try:
                self.journal(kind, **fields)
            except Exception:
                pass

    def _changed(self) -> None:
        self.changes += 1
        self.changed_at = self.clock()
        self.reals.clear()
        self.draws.clear()

    def _to(self, phase: str) -> None:
        self.phase = phase
        self.since = self.clock()

    @property
    def owned(self) -> bool:
        return bool(self.gpu.owned)

    def settling(self) -> bool:
        return self.phase in ("settle", "verify") or self.clock() - self.changed_at < SETTLE_S

    def _release(self, why: str) -> None:
        if self.gpu.owned or self.gpu.phase == "restore-pending":
            r = self.gpu.restore()
            self._note("gpu-clock-restore", reason=why, restored=bool(r.get("restored")))
            self._changed()
        self.baseline = None
        self.steps = 0

    def tick(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        """ctx: enabled, game, app, steady, menu, point, real, sensors, draw_w, other_busy."""
        now = self.clock()
        if self.gpu.phase == "restore-pending":
            self.gpu.restore()
        key = str(ctx.get("app") or "") if ctx.get("game") else None
        if key != self.key:
            self._release("game-changed")
            self.key = key
            self.blocked_until = 0.0
            self._to("observe")
        if not ctx.get("enabled") or not ctx.get("game"):
            self._release("off" if ctx.get("game") else "no-game")
            self._to("off")
            return self._status("off" if not ctx.get("enabled") else "no-game")
        if not ctx.get("steady") or ctx.get("menu") or ctx.get("other_busy"):
            # The point is being measured or tried, or Power Split runs: the player's clock back.
            if self.gpu.owned:
                self._release("not-steady")
            self._to("observe")
            return self._status("waiting")
        sensors = ctx.get("sensors") or {}
        real, point, draw = ctx.get("real"), float(ctx.get("point") or 0), ctx.get("draw_w")
        if real is not None:
            self.reals.append(float(real))
        if draw is not None:
            self.draws.append(float(draw))
        cpu, gpu = sensors.get("cpu_top_core_pct"), sensors.get("gpu_busy_pct")
        bound = cpu is not None and gpu is not None and cpu >= CPU_BOUND_PCT and gpu <= GPU_LIGHT_PCT

        # Insurance: real frames clearly under the point lift the clock at once.
        recent = list(self.reals)[-3:]
        if self.gpu.owned and len(recent) == 3 and point and statistics.median(recent) < GUARD_RATIO * point:
            r = self.gpu.raise_ceiling()
            self._note("gpu-clock", reason="real-frames-short", limit_mhz=self.gpu.applied_max, applied=r.get("applied"))
            self._changed()
            self.blocked_until = now + REJECT_S
            self._to("hold")
            return self._status("lifted")

        if self.phase == "observe":
            if not bound:
                self.since = now
            elif (now - self.since >= OBSERVE_S and now >= self.blocked_until and self.steps < MAX_STEPS
                  and len(self.draws) >= 10):
                self._step(now, sensors)
        elif self.phase == "settle":
            if now - self.since >= SETTLE_S:
                self.reals.clear()
                self.draws.clear()
                self._to("verify")
        elif self.phase == "verify":
            if now - self.since >= VERIFY_S and self.baseline is not None:
                self._judge(now, point)
        elif self.phase == "hold":
            if now - self.since >= HOLD_S:
                self._to("observe")
        return self._status("running")

    def _step(self, now: float, sensors: Dict[str, Any]) -> None:
        self.baseline = {"draw": statistics.median(self.draws),
                         "real": statistics.median(self.reals) if self.reals else 0.0}
        r = self.gpu.lower_ceiling(sensors.get("gpu_clock_mhz"))
        if not r.get("applied"):
            self._note("gpu-clock-skipped", reason=r.get("reason"))
            self.blocked_until = now + REJECT_S
            self.baseline = None
            return
        self.steps += 1
        self._note("gpu-clock", reason="cpu-bound-step-down", limit_mhz=r.get("limit_mhz"),
                   draw_before=round(self.baseline["draw"], 2))
        self._changed()
        self._to("settle")

    def _judge(self, now: float, point: float) -> None:
        assert self.baseline is not None
        if min(len(self.reals), len(self.draws)) < COVERAGE * VERIFY_S:
            # Too few readings to prove anything: the step is not kept on a guess.
            r = self.gpu.raise_ceiling()
            self._note("gpu-clock-rejected", reason="no-data", reals=len(self.reals), draws=len(self.draws),
                       back_to=self.gpu.applied_max, applied=r.get("applied"))
            self._changed()
            self.blocked_until = now + REJECT_S
            self._to("hold")
            return
        real = statistics.median(self.reals) if self.reals else 0.0
        draw = statistics.median(self.draws) if self.draws else self.baseline["draw"]
        held = point > 0 and real >= HOLD_RATIO * point
        saved = self.baseline["draw"] - draw
        if held and saved >= MIN_SAVING_W:
            self._note("gpu-clock-kept", limit_mhz=self.gpu.applied_max, saved_w=round(saved, 2), real=round(real, 1))
            self._to("hold")
            return
        r = self.gpu.raise_ceiling()
        self._note("gpu-clock-rejected", reason="frames" if not held else "no-saving", saved_w=round(saved, 2),
                   real=round(real, 1), back_to=self.gpu.applied_max, applied=r.get("applied"))
        self._changed()
        self.blocked_until = now + REJECT_S
        self._to("hold")

    def _status(self, state: str) -> Dict[str, Any]:
        self.status = {"phase": self.phase, "state": state, "owned": self.gpu.owned,
                       "limit_mhz": self.gpu.applied_max if self.gpu.owned else None, "steps": self.steps,
                       "blocked_s": max(0, round(self.blocked_until - self.clock()))}
        return self.status

    def stop(self) -> None:
        self._release("unload")
