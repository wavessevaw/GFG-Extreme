"""Frame-generation point pilot: GSF Kedavra Auto and the GFG Extreme Autopilot as one.

A "point" is the game's base frame cap; KEDAVRA generates the rest of the refresh. At 90 Hz
the ladder is 24 (x3.75), 30 (x3), 35 (x2.6), 40 (x2.25), 45 (x2); at 60 Hz 20 (x3), 25, 30.

GFG Extreme's principles, with Kedavra Auto as the measuring instrument:

  MEASURE  the TDP is held at the ceiling and KEDAVRA Auto finds, vblank by vblank, the
           highest cap the game holds (it counts late frames, which a 1 s average cannot).
           The pilot waits until Auto stays on one cap for 12 s (at most 45 s, then the median).
  LOCK     the point is fixed as the engine's base cap: no more Auto trials, an even cadence,
           and the Governor looks for the lowest TDP that still holds it.
  GUARD    every 5 s the pilot checks the game against the point. If it falls short while
           the TDP is at the ceiling (the game itself got heavier), the point steps down at
           once to the highest cap the game's frame rate holds. A shortfall below the ceiling
           is the Governor's: it raises the TDP (to the ceiling at once when severe).
  ADAPT    Quality and Balanced try the next point up after 2 min clean (backing off to 16
           min after failed tries): TDP at the ceiling, 6 s trial, kept only if the game holds.

Objectives: Quality and Balanced climb to the top of the ladder (Balanced then saves watts
with a margin, Quality keeps the player's TDP). Battery locks the lowest point, x3.75 at 90 Hz
(x3 at 60 Hz): the game renders the fewest frames, generation fills the screen. Any objective
falls back to x3.75 when a game cannot hold x3 even at full power: frames held 3-4 refreshes
look smoother than x3 with repeated frames.

Fixed choices (x2, x3, x3.75, a custom cap) are never changed by the pilot; it only reports when
the chosen point does not hold.
"""
from __future__ import annotations

import statistics
import time
from collections import deque
from typing import Any, Callable, Deque, Dict, List, Optional

STABLE_S = 12.0
MEASURE_MIN_S = 8.0
MEASURE_MAX_S = 45.0
GUARD_S = 5.0
TRIAL_S = 6.0
PROMOTE_WAIT_S = 120.0
PROMOTE_WAIT_MAX_S = 960.0
# Headroom: the GPU (or the CPU) clearly not at its limit at the locked point means the game
# could run the next point up. Then the next point is tried after HEADROOM_WAIT_S of clean play,
# whatever the back-off, so a lighter scene gets its real frames back within seconds.
MEASURE_GAP_S = 2.5   # seconds without a confirmed Auto cap that break a measurement
HEADROOM_WAIT_S = 10.0
HEADROOM_GPU_PCT = 92.0      # the GPU at the next point is estimated to stay under this
HEADROOM_CPU_PCT = 85.0
HOLD_RATIO = 0.95       # real fps vs cap over a guard window
TRIAL_RATIO = 0.97
PACE_MIN = 0.99


def div_up(a: int, b: int) -> int:
    return (a + b - 1) // b


def ladder(refresh: int) -> List[int]:
    """Base caps for a refresh rate, ascending (same steps as kfg_auto, plus x3.75)."""
    refresh = max(30, int(refresh))
    lo, hi = div_up(refresh, 3), refresh // 2
    floor = max(20, div_up(refresh * 4, 15))
    out = [floor] if floor < lo else []
    out.append(lo)
    c = (lo // 5 + 1) * 5
    while c < hi:
        out.append(c)
        c += 5
    if hi > lo:
        out.append(hi)
    return out


def x375_cap(refresh: int) -> int:
    return ladder(refresh)[0]


def mult_label(refresh: int, cap: int) -> str:
    if cap <= 0:
        return "off"
    v = refresh / cap
    if abs(v * 4 - round(v * 4)) < 0.01:
        return "x" + f"{round(v * 4) / 4:.2f}".rstrip("0").rstrip(".")
    return f"x{v:.1f}"


class PointPilot:
    def __init__(self, clock: Callable[[], float] = time.monotonic,
                 journal: Optional[Callable[..., None]] = None) -> None:
        self.clock = clock
        self.journal = journal
        self.reset()

    def reset(self) -> None:
        self.context: Optional[tuple] = None
        self.phase = "idle"
        self.point = 0
        self.reason = ""
        self.since = self.clock()
        self.caps: Deque[tuple] = deque(maxlen=120)  # (t, engine cap) during measure
        self.window: List[Dict[str, Any]] = []
        self.window_done: List[Dict[str, Any]] = []
        self.window_start = self.clock()
        self.clean_since: Optional[float] = None
        self.promote_wait = PROMOTE_WAIT_S
        self.headroom_backoff = 0.0  # after a failed trial the headroom estimate waits this long
        self.trial_cap = 0
        self.trial_from = 0
        self.holds = True
        self.demotions = 0
        self.promotions = 0

    def _note(self, kind: str, **fields: Any) -> None:
        if self.journal:
            try:
                self.journal(kind, **fields)
            except Exception:
                pass

    def _go(self, phase: str, reason: str, point: Optional[int] = None) -> None:
        now = self.clock()
        if point is not None:
            self.point = point
        self._note("pilot", phase=phase, was=self.phase, point=self.point, reason=reason)
        self.phase, self.reason, self.since = phase, reason, now
        self.window, self.window_start = [], now
        self.clean_since = None

    # ------------------------------------------------------------------ request
    @staticmethod
    def _request(multiplier: int, base: int, floor: int, hold: bool) -> Dict[str, Any]:
        return {"multiplier": multiplier, "base_fps": base, "auto_floor": floor, "hold_ceiling": hold}

    def tick(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        """ctx: fg, base_fps, objective (quality|balanced|battery), refresh, game (bool), app,
        engine (status dict), real (game fps over the last second or None), pace, confirmed
        (the engine runs the policy the pilot asked for), at_ceiling (TDP at the ceiling or not
        managed)."""
        fg = ctx.get("fg", "auto")
        refresh = int(ctx.get("refresh") or 90)
        steps = ladder(refresh)
        objective = ctx.get("objective", "balanced")
        context = (ctx.get("app"), refresh, fg, objective, int(ctx.get("base_fps") or 0))
        if context != self.context:
            keep = (self.context is not None and self.context[:3] == context[:3] and self.point
                    and self.context[3] != "battery")
            old_point = self.point
            self.reset()
            self.context = context
            if keep and fg == "auto":
                self.point = old_point  # an objective change keeps the measured point
        if fg == "off":
            self.phase, self.point = "off", 0
            return {**self._request(0, 0, 0, False), **self.snapshot(refresh)}
        if fg in ("x2", "x3"):
            self.phase, self.point = "fixed", div_up(refresh, int(fg[1]))
            req = self._request(int(fg[1]), 0, 0, False)
            self._guard_fixed(ctx)
            return {**req, **self.snapshot(refresh)}
        if fg in ("x3.75", "custom"):
            cap = x375_cap(refresh) if fg == "x3.75" else max(20, min(refresh, int(ctx.get("base_fps") or 45)))
            self.phase, self.point = "fixed", cap
            self._guard_fixed(ctx)
            return {**self._request(1, cap, 0, False), **self.snapshot(refresh)}
        return {**self._auto(ctx, steps, objective), **self.snapshot(refresh)}

    def _guard_fixed(self, ctx: Dict[str, Any]) -> None:
        verdict = self._window(ctx, self.point, GUARD_S)
        if verdict is not None:
            self.holds = verdict["ok"] or not verdict["at_ceiling"]
            self.reason = "" if self.holds else "the game does not hold this point even at full power"

    def _window(self, ctx: Dict[str, Any], cap: int, length: float) -> Optional[Dict[str, Any]]:
        """Collect samples; a verdict when the window is full. Samples taken while the engine
        does not run this policy yet are not counted."""
        now = self.clock()
        # "settling": Power Split is trying a CPU clock level; its own guard lifts the cap on a
        # dip, so those seconds say nothing about the point.
        if not ctx.get("game") or not ctx.get("confirmed") or ctx.get("real") is None or ctx.get("settling"):
            self.window, self.window_start = [], now
            return None
        self.window.append({"real": float(ctx["real"]), "pace": ctx.get("pace"),
                            "ceiling": bool(ctx.get("at_ceiling", True)),
                            "gpu": ctx.get("gpu_busy"), "cpu": ctx.get("cpu_top")})
        if now - self.window_start < length:
            return None
        self.window_done = self.window
        reals = [s["real"] for s in self.window]
        paces = [s["pace"] for s in self.window if s["pace"] is not None]
        real = statistics.fmean(reals)
        pace = statistics.fmean(paces) if paces else None
        self.window, self.window_start = [], now
        ok = real >= HOLD_RATIO * cap and (pace is None or pace >= PACE_MIN)
        gpus = [x["gpu"] for x in self.window_done if isinstance(x.get("gpu"), (int, float))]
        cpus = [x["cpu"] for x in self.window_done if isinstance(x.get("cpu"), (int, float))]
        return {"ok": ok, "real": real, "median": statistics.median(reals), "pace": pace,
                "at_ceiling": all(x["ceiling"] for x in self.window_done),
                "gpu": statistics.median(gpus) if len(gpus) * 2 >= len(self.window_done) else None,
                "cpu": statistics.median(cpus) if len(cpus) * 2 >= len(self.window_done) else None}

    def _auto(self, ctx: Dict[str, Any], steps: List[int], objective: str) -> Dict[str, Any]:
        now = self.clock()
        top = steps[0] if objective == "battery" else steps[-1]
        if not ctx.get("game"):
            self.phase = "idle"
            return self._request(1, 0, steps[0], False)
        if self.phase in ("idle",):
            if objective == "battery":
                self._go("locked", "Battery: the lowest point, generation fills the refresh", steps[0])
            elif self.point:
                self._go("locked", "kept the measured point", min(self.point, top))
            else:
                self.caps.clear()
                self._go("measure", "measuring the game at full power")
        if self.phase == "measure":
            return self._measure(ctx, steps, top)
        if self.phase == "trial":
            return self._trial(ctx, steps)
        # locked
        if self.point > top:
            self._go("locked", "objective lowered the point", top)
        verdict = self._window(ctx, self.point, GUARD_S)
        if verdict is not None:
            if verdict["ok"]:
                self.holds = True
                if self.clean_since is None:
                    self.clean_since = now
                nxt = [c for c in steps if c > self.point]
                if nxt and objective != "battery" and self._headroom(verdict, self.point, nxt[0]):
                    self.promote_wait = min(self.promote_wait, max(HEADROOM_WAIT_S, self.headroom_backoff))
            else:
                self.clean_since = None
                if verdict["at_ceiling"]:
                    # Short at full power the whole window: the game got heavier.
                    lower = [c for c in steps if c < self.point]
                    fit = [c for c in lower if TRIAL_RATIO * c <= verdict["median"]]
                    if lower:
                        new = fit[-1] if fit else lower[0]
                        self.demotions += 1
                        self.promote_wait = PROMOTE_WAIT_S
                        self._go("locked", f"game fell to {verdict['median']:.0f} fps at full power: "
                                 f"point {self.point} -> {new}", new)
                    else:
                        self.holds = False
                        self.reason = "the game does not hold the lowest point even at full power"
        if (objective != "battery" and self.clean_since is not None and self.point < top
                and now - self.clean_since >= self.promote_wait and ctx.get("at_ceiling_possible", True)):
            nxt = [c for c in steps if c > self.point][0]
            self.trial_cap, self.trial_from = nxt, self.point
            self._go("trial", f"trying point {nxt}")
            return self._request(1, self.trial_from, 0, True)  # raise the TDP first
        return self._request(1, self.point, 0, False)

    @staticmethod
    def _headroom(verdict: Dict[str, Any], point: int, nxt: int) -> bool:
        """The game has room for the next point: GPU load scaled to it stays under the limit,
        and the busiest CPU core is not near its own."""
        gpu, cpu = verdict.get("gpu"), verdict.get("cpu")
        if gpu is None or gpu <= 0:
            return False
        if cpu is not None and cpu * nxt / point >= HEADROOM_CPU_PCT:
            return False
        return gpu * nxt / point < HEADROOM_GPU_PCT

    def _measure(self, ctx: Dict[str, Any], steps: List[int], top: int) -> Dict[str, Any]:
        now = self.clock()
        st = ctx.get("engine") or {}
        if ctx.get("confirmed") and st.get("auto") and ctx.get("game"):
            cap = int(st.get("cap_fps") or 0)
            if cap:
                self.caps.append((now, cap))
        if self.caps and now - self.caps[-1][0] > MEASURE_GAP_S:
            # No fresh confirmed reading: silence is not stability, the measurement restarts.
            self.caps.clear()
        elapsed = now - self.since
        if self.caps:
            last = self.caps[-1][1]
            stable_from = now
            for t, c in reversed(self.caps):
                if c != last:
                    break
                stable_from = t
            choice = None
            if elapsed >= MEASURE_MIN_S and now - stable_from >= STABLE_S:
                choice = last
            elif elapsed >= MEASURE_MAX_S:
                choice = int(statistics.median(c for _, c in self.caps))
            if choice:
                fit = [c for c in steps if c <= choice] or [steps[0]]
                point = min(fit[-1], top)
                self._go("locked", f"measured: the game holds {choice} fps; locked {point}", point)
                return self._request(1, point, 0, False)
        elif elapsed >= MEASURE_MAX_S:
            self._go("locked", "no measurement (no game frames): x3", steps[1] if len(steps) > 1 else steps[0])
            return self._request(1, self.point, 0, False)
        return self._request(1, 0, steps[0], True)

    def _trial(self, ctx: Dict[str, Any], steps: List[int]) -> Dict[str, Any]:
        if not ctx.get("at_ceiling", True):
            # Waiting for the Governor to bring the TDP to the ceiling.
            self.window, self.window_start = [], self.clock()
            return self._request(1, self.trial_from, 0, True)
        verdict = self._window(ctx, self.trial_cap, TRIAL_S)
        if verdict is None:
            return self._request(1, self.trial_cap, 0, True)
        if verdict["ok"] and verdict["real"] >= TRIAL_RATIO * self.trial_cap:
            self.promotions += 1
            self.promote_wait = 30.0  # keep climbing soon while it holds
            self.headroom_backoff = 0.0
            self._go("locked", f"point {self.trial_cap} holds: locked", self.trial_cap)
            self.clean_since = self.clock()
        else:
            self.promote_wait = min(PROMOTE_WAIT_MAX_S, self.promote_wait * 2)
            self.headroom_backoff = min(480.0, max(60.0, self.headroom_backoff * 2))
            self._go("locked", f"point {self.trial_cap} did not hold; next try in {self.promote_wait:.0f} s",
                     self.trial_from)
        return self._request(1, self.point, 0, False)

    def snapshot(self, refresh: int = 90) -> Dict[str, Any]:
        return {"phase": self.phase, "point": self.point, "label": mult_label(refresh, self.point),
                "reason": self.reason, "holds": self.holds, "demotions": self.demotions,
                "promotions": self.promotions, "trial_cap": self.trial_cap if self.phase == "trial" else 0}
