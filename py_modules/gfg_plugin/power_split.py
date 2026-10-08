"""Smart power split: the CPU's boost clock gives the GPU its watts back in GPU-bound games.

On the Steam Deck CPU and GPU share one power limit.  A game that waits on the GPU still lets its
CPU cores boost to 3.5 GHz between frames, and every watt they take is a watt the GPU does not get.
When the game is GPU-bound (or at the Governor's power cap) and its busiest core has headroom,
this module lowers the CPU's maximum clock one level at a time.  The GPU then runs faster at the
same TDP, and the Governor's own search turns that into fewer watts for the same real frames.

Real frames come first:

* a step down needs the point's real cadence held and the busiest core predicted under
  ``CPU_PLAN`` % at the lower clock;
* every step is a ``PROBE_S`` trial; real frames under ``DIP_FPS`` of the point's real rate or a
  busiest core over ``CPU_HIGH`` % lift the cap at once (a level that failed with the CPU busy is
  not tried again for ``FAIL_TTL_S``);
* loading screens and menus (not eligible) run uncapped.

**Measured, not assumed.**  While a level holds, A-B-A windows now and then lift the cap for a
moment (``ab-control``) and compare GPU clock per watt with and without it.  ``SplitMemory`` keeps
the pairs per game across sessions; a game where the split measurably does nothing (the 99 %
interval's top under ``USELESS_PCT``) gets it switched off at its next session start, and is
re-checked after ``RECHECK_SESSIONS`` sessions.

Pure logic with an injected clock: the Governor calls ``step`` every iteration and applies
``cap_khz``.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .frame_os.proof import stats

LEVELS = (1.0, 0.85, 0.7, 0.6, 0.5)     # share of the CPU's maximum clock
FLOOR_KHZ = 1_600_000                   # never below this, whatever the hardware allows
PROBE_S = 10.0
PROBE_SETTLE_S = 3.0                    # the FPS window still holds frames from before the step
STEP_GAP_S = 20.0
COOLDOWN_S = 60.0
FAIL_TTL_S = 600.0
HOLD_FPS = 0.97                         # of the point's real rate, to step down
DIP_FPS = 0.93                          # under this the cap comes off at once
CPU_HIGH = 90.0
CPU_PLAN = 80.0
GPU_BOUND = 85.0
POWER_BOUND = 0.95
# A/B: before (capped) -> control (cap lifted) -> after (capped)
AB_WINDOW_S = 8.0
AB_SETTLE_S = 2.0
AB_GAP_S = 60.0
AB_SETTLED_GAP_S = 240.0
AB_SETTLED_PAIRS = 8
AB_MIN_FILL = 0.6
# per game
KEEP_PAIRS = 40
MIN_OFF_PAIRS = 8
USELESS_PCT = 1.0
RECHECK_SESSIONS = 8


@dataclass
class Sample:
    real_fps: Optional[float]
    target_real: float
    top_core_pct: Optional[float]
    gpu_busy_pct: Optional[float]
    gpu_mhz: Optional[float]
    draw_w: Optional[float]
    tdp_w: Optional[float]
    steady: bool = True          # the Governor holds its point and watts (A/B checks only then)


def _ok(v: Any) -> bool:
    return isinstance(v, (int, float)) and math.isfinite(float(v))


def levels_khz(max_khz: int, min_khz: int = 0) -> List[int]:
    """The ladder for this CPU: level 0 is no cap (the maximum)."""
    floor = max(FLOOR_KHZ, int(min_khz or 0))
    out: List[int] = []
    for share in LEVELS:
        khz = max(floor, int(round(max_khz * share / 100_000.0)) * 100_000)
        if not out or khz < out[-1]:
            out.append(khz)
    return out if max_khz > floor else [int(max_khz)]


class _Window:
    def __init__(self, start: float) -> None:
        self.start = start
        self.sums: Dict[str, float] = {}
        self.covered: Dict[str, float] = {}

    def add(self, dt: float, **values: Optional[float]) -> None:
        for key, v in values.items():
            if _ok(v) and float(v) > 0:
                self.sums[key] = self.sums.get(key, 0.0) + float(v) * dt
                self.covered[key] = self.covered.get(key, 0.0) + dt

    def mean(self, key: str) -> Optional[float]:
        if self.covered.get(key, 0.0) < AB_MIN_FILL * AB_WINDOW_S:
            return None
        return self.sums[key] / self.covered[key]


class PowerSplit:
    """One game session's CPU clock cap: ``off -> probe -> hold`` with A/B checks while holding."""

    def __init__(self, ladder_khz: List[int]) -> None:
        self.ladder = list(ladder_khz) or [0]
        self.enabled = True
        self.level = 0
        self.phase = "off"
        self.reason = "starting"
        self.since = 0.0
        self.next_at: Optional[float] = None
        self.failed: Dict[int, float] = {}       # level -> until
        self.start_level = 0                     # remembered from earlier sessions
        self.best_level = 0                      # deepest level that held this session
        self.pairs: List[Dict[str, float]] = []  # this session's A/B pairs
        self.ab_phase: Optional[str] = None
        self._ab: Dict[str, Any] = {}
        self._last: Optional[float] = None
        self.prior_pairs: List[float] = []
        self.last_change: Optional[Dict[str, Any]] = None

    # ------------------------------------------------------------------ output
    @property
    def cap_khz(self) -> Optional[int]:
        """The clock to apply, or None for no cap (the user's own limit)."""
        level = 0 if self.ab_phase == "control" else self.level
        return self.ladder[level] if level > 0 else None

    # ------------------------------------------------------------------ input
    def step(self, now: float, eligible: bool, s: Sample) -> Optional[int]:
        dt = 0.0 if self._last is None else max(0.0, min(2.0, now - self._last))
        self._last = now
        self.last_change = None
        if not self.enabled or not eligible or len(self.ladder) < 2:
            self._abort_ab()
            if self.level:
                self._move(now, 0, "not-eligible" if self.enabled else "switched-off")
            self.phase, self.reason = "off", ("not-eligible" if self.enabled else "switched-off")
            self.next_at = None
            return self.cap_khz
        if self.next_at is None:
            self.next_at = now + STEP_GAP_S          # let the game settle at its point first
            self.phase, self.reason = "free", "settling"
        if self._guard(now, s):
            return self.cap_khz
        if self.ab_phase is not None:
            self._ab_step(now, dt, s)
            return self.cap_khz
        if self.phase == "probe":
            if now - self.since >= PROBE_S:
                self.phase, self.reason = "hold", "held"
                self.best_level = max(self.best_level, self.level)
                self.next_at = now + STEP_GAP_S
            return self.cap_khz
        if now < self.next_at:
            return self.cap_khz
        if self.level and s.steady and self._ab_due(now):
            self._ab_start(now, s)
            return self.cap_khz
        nxt = self._next_level(now, s)
        if nxt is not None:
            self._move(now, nxt, "step-down")
            self.phase, self.reason = "probe", "trying-lower-cpu-clock"
        else:
            self.next_at = now + STEP_GAP_S
        return self.cap_khz

    # ------------------------------------------------------------------ rules
    def _guard(self, now: float, s: Sample) -> bool:
        """Real frames short or the CPU near its limit: lift the cap now.  True if it acted."""
        if self.level == 0 and self.ab_phase is None:
            return False
        settled = now - self.since >= PROBE_SETTLE_S
        dip = settled and _ok(s.real_fps) and s.real_fps < DIP_FPS * s.target_real
        busy = _ok(s.top_core_pct) and s.top_core_pct >= CPU_HIGH
        if not (dip or busy):
            return False
        self._abort_ab()
        level = self.level
        if busy and (dip or self.phase == "probe"):
            self.failed[level] = now + FAIL_TTL_S
        target = 0 if dip else level - 1
        self._move(now, target, "real-frames-short" if dip else "cpu-busy")
        self.phase, self.reason = ("free" if target == 0 else "hold"), ("real-frames-short" if dip else "cpu-busy")
        self.next_at = now + COOLDOWN_S
        return True

    def _next_level(self, now: float, s: Sample) -> Optional[int]:
        if self.level + 1 >= len(self.ladder):
            return None
        if not (_ok(s.real_fps) and s.real_fps >= HOLD_FPS * s.target_real):
            return None
        gpu_bound = _ok(s.gpu_busy_pct) and s.gpu_busy_pct >= GPU_BOUND
        power_bound = _ok(s.draw_w) and _ok(s.tdp_w) and s.tdp_w > 0 and s.draw_w >= POWER_BOUND * s.tdp_w
        if not (gpu_bound or power_bound):
            return None
        # a remembered level is the first stop when this session has not been there yet
        nxt = self.level + 1
        if self.level == 0 and self.start_level > 1 and not self.failed:
            nxt = min(self.start_level, len(self.ladder) - 1)
        while nxt > self.level and self.failed.get(nxt, -1e9) > now:
            nxt -= 1
        if nxt <= self.level:
            return None
        if not _ok(s.top_core_pct):
            return None
        predicted = s.top_core_pct * self.ladder[self.level] / self.ladder[nxt]
        if predicted > CPU_PLAN:
            return None
        return nxt

    def _move(self, now: float, level: int, why: str) -> None:
        if level == self.level:
            return
        self.last_change = {"from_khz": self.ladder[self.level], "to_khz": self.ladder[level],
                            "level": level, "reason": why}
        self.level, self.since = level, now

    # ------------------------------------------------------------------ A/B
    def _ab_due(self, now: float) -> bool:
        if self.phase != "hold":
            return False
        settled = len(self.prior_pairs) + len(self.pairs) >= AB_SETTLED_PAIRS
        last = self._ab.get("done_at")
        return last is None or now - last >= (AB_SETTLED_GAP_S if settled else AB_GAP_S)

    def _ab_start(self, now: float, s: Sample) -> None:
        self.ab_phase = "before"
        self._ab.update({"window": _Window(now), "tdp": s.tdp_w, "level": self.level, "means": {}})

    def _ab_step(self, now: float, dt: float, s: Sample) -> None:
        ab = self._ab
        if s.tdp_w != ab["tdp"] or self.level != ab["level"]:
            self._abort_ab()                      # the Governor moved the watts: no fair comparison
            return
        window: _Window = ab["window"]
        settle = 0.0 if self.ab_phase == "before" else AB_SETTLE_S
        if now - window.start >= settle:
            window.add(dt, mhz=s.gpu_mhz, draw=s.draw_w, real=s.real_fps)
        if now - window.start < settle + AB_WINDOW_S:
            return
        mhz, draw = window.mean("mhz"), window.mean("draw")
        if mhz is None or draw is None:
            self._abort_ab()
            return
        ab["means"][self.ab_phase] = {"eff": mhz / draw, "draw": draw, "mhz": mhz,
                                      "real": window.mean("real") or 0.0}
        nxt = {"before": "control", "control": "after"}.get(self.ab_phase)
        if nxt is not None:
            self.ab_phase, ab["window"] = nxt, _Window(now)
            if nxt == "control":
                self.since = now                  # the guard's settle covers the lifted cap too
            return
        m = ab["means"]
        free = m["control"]
        capped = {k: (m["before"][k] + m["after"][k]) / 2.0 for k in ("eff", "draw", "mhz", "real")}
        self.pairs.append({
            "gain": round(100.0 * (capped["eff"] - free["eff"]) / free["eff"], 2),
            "draw": round(100.0 * (free["draw"] - capped["draw"]) / free["draw"], 2),
            "mhz": round(100.0 * (capped["mhz"] - free["mhz"]) / free["mhz"], 2),
            "real": round(capped["real"] - free["real"], 2),
            "khz": self.ladder[self.level],
        })
        self.ab_phase = None
        ab["done_at"] = now
        self.since = now

    def _abort_ab(self) -> None:
        if self.ab_phase is not None:
            self.ab_phase = None
            self._ab["done_at"] = self._last if self._last is not None else 0.0

    # ------------------------------------------------------------------ results
    def summary(self) -> Dict[str, Any]:
        gains = self.prior_pairs + [p["gain"] for p in self.pairs]
        s = stats(gains)
        last = self.pairs[-1] if self.pairs else None
        return {"enabled": self.enabled, "phase": self.phase, "reason": self.reason, "level": self.level,
                "cap_khz": self.cap_khz, "max_khz": self.ladder[0], "ab": self.ab_phase,
                "gain_pct": s["mean"], "gain_low": s["low"], "gain_high": s["high"],
                "pairs": s["n"], "session_pairs": len(self.pairs), "measured": s["measured"],
                "draw_pct": last["draw"] if last else None, "mhz_pct": last["mhz"] if last else None}


class SplitMemory:
    """One game's record: ``{"level", "pairs", "pair_sessions", "sessions", "off"}``."""

    def __init__(self, record: Optional[Dict[str, Any]] = None) -> None:
        record = record if isinstance(record, dict) else {}
        self.level = int(record.get("level") or 0) if _ok(record.get("level")) else 0
        self.pairs = [float(v) for v in (record.get("pairs") or []) if _ok(v)][-KEEP_PAIRS:]
        self.pair_sessions = int(record.get("pair_sessions") or 0) if _ok(record.get("pair_sessions")) else 0
        self.sessions = int(record.get("sessions") or 0) if _ok(record.get("sessions")) else 0
        off = record.get("off")
        self.off: Optional[int] = int(off) if _ok(off) else None
        self.ruled_out = False
        self._seen = 0           # pairs of the current session already taken
        self._added = False      # the current session counted in pair_sessions

    def disabled(self) -> bool:
        return self.off is not None and self.sessions - self.off < RECHECK_SESSIONS

    def start_session(self) -> bool:
        """Decide once per session (never per new pair); True if the split is off for this game."""
        self.ruled_out = False
        self._seen, self._added = 0, False
        if self.off is None and len(self.pairs) >= MIN_OFF_PAIRS and self.pair_sessions >= 2:
            strict = stats(self.pairs, confidence=0.99)
            if strict["high"] is not None and strict["high"] < USELESS_PCT:
                self.off = self.sessions + 1
                self.ruled_out = True
        self.sessions += 1
        if self.off is not None and self.sessions - self.off >= RECHECK_SESSIONS:
            self.off, self.pairs, self.pair_sessions, self.level = None, [], 0, 0
        return self.disabled()

    def record(self, split: PowerSplit) -> bool:
        """Take this session's new pairs and its deepest held level; True if anything changed.
        Called as they come (a pair every 1-4 min), so an unload loses nothing."""
        changed = False
        new = [p["gain"] for p in split.pairs[self._seen:]]
        self._seen = len(split.pairs)
        if new:
            self.pairs = (self.pairs + new)[-KEEP_PAIRS:]
            if not self._added:
                self._added = True
                self.pair_sessions += 1
            changed = True
        if split.best_level and split.best_level != self.level:
            self.level = split.best_level
            changed = True
        return changed

    def to_record(self) -> Dict[str, Any]:
        return {"level": self.level, "pairs": [round(v, 2) for v in self.pairs],
                "pair_sessions": self.pair_sessions, "sessions": self.sessions, "off": self.off}
