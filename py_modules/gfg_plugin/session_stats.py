"""Per-game-session numbers for the player: how long, how smooth, how many watts.

The Governor feeds one sample per loop iteration while a managed game runs and FPS telemetry is
fresh.  Averages are time-weighted (each sample counts for the time since the previous one, capped
so a pause in telemetry cannot dominate).  ``reference_w`` is the TDP limit the Deck had before the
Governor took over, i.e. what the game would have been allowed without GFG.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

MAX_STEP_S = 5.0
MIN_SESSION_S = 30.0


class SessionStats:
    def __init__(self) -> None:
        self.key: Optional[tuple] = None
        self._reset()

    def _reset(self) -> None:
        self.started: Optional[float] = None
        self.last: Optional[float] = None
        self.seconds = 0.0
        self._sums: Dict[str, float] = {}
        self._weights: Dict[str, float] = {}
        self.reference_w: Optional[float] = None

    def start(self, key: Any, now: float) -> None:
        self.key = tuple(key) if isinstance(key, (list, tuple)) else key
        self._reset()
        self.started = self.last = now

    def add(self, now: float, *, output: Optional[float], real: Optional[float], tdp: Optional[float],
            draw: Optional[float], reference_w: Optional[float]) -> None:
        if self.started is None or self.last is None:
            return
        dt = min(MAX_STEP_S, max(0.0, now - self.last))
        self.last = now
        if dt <= 0:
            return
        self.seconds += dt
        for name, value in (("output", output), ("real", real), ("tdp", tdp), ("draw", draw)):
            if isinstance(value, (int, float)) and value > 0:
                self._sums[name] = self._sums.get(name, 0.0) + float(value) * dt
                self._weights[name] = self._weights.get(name, 0.0) + dt
        if isinstance(reference_w, (int, float)) and reference_w > 0:
            self.reference_w = float(reference_w)

    def _avg(self, name: str) -> Optional[float]:
        weight = self._weights.get(name, 0.0)
        return round(self._sums[name] / weight, 1) if weight > 0 else None

    def summary(self) -> Optional[Dict[str, Any]]:
        if self.started is None or self.seconds < MIN_SESSION_S:
            return None
        tdp = self._avg("tdp")
        return {
            "minutes": round(self.seconds / 60.0, 1),
            "avg_output_fps": self._avg("output"),
            "avg_real_fps": self._avg("real"),
            "avg_tdp_w": tdp,
            "avg_draw_w": self._avg("draw"),
            "reference_w": self.reference_w,
            "saved_w": round(self.reference_w - tdp, 1) if self.reference_w and tdp else None,
        }

    def finish(self) -> Optional[Dict[str, Any]]:
        result = self.summary()
        self.key = None
        self._reset()
        return result
