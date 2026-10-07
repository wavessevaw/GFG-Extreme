"""Scene-change detection from the frame-cost timeline.  (GFG Frame OS.)

A cut, a door into a new area, a menu over the game: the GPU cost per real frame jumps.  Those
are exactly the moments a generated frame (interpolated between two unrelated images) looks
wrong, so the policy buys a short burst of real frames.  Input is the scheduler's frame cost
(ms) from the gfg-pacer telemetry, one value per tick.
"""
from __future__ import annotations

from typing import Optional

JUMP_RATIO = 1.4
DROP_RATIO = 0.7
REFRACTORY_S = 2.0
EWMA = 0.2


class SceneChangeDetector:
    def __init__(self) -> None:
        self.baseline: Optional[float] = None
        self._last_event = -1e9

    def tick(self, now: float, cost_ms: Optional[float]) -> bool:
        if cost_ms is None or cost_ms <= 0:
            return False
        if self.baseline is None:
            self.baseline = cost_ms
            return False
        ratio = cost_ms / self.baseline
        changed = (ratio >= JUMP_RATIO or ratio <= DROP_RATIO) and now - self._last_event >= REFRACTORY_S
        if changed:
            self._last_event = now
            self.baseline = cost_ms          # the new scene is the new normal
        else:
            self.baseline += EWMA * (cost_ms - self.baseline)
        return changed
