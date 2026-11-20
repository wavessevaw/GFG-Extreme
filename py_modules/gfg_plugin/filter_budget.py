"""Under sustained GPU pressure, reduce anti-aliasing and optional sharpening.
Colour and style effects are explicit profile choices in every performance mode.
Quality always keeps the complete profile.
"""
from __future__ import annotations

import time
from typing import Any, Callable, Dict, Optional

SHED_S = 20.0
BACK_S = 90.0
BUSY_PCT = 90.0
IDLE_PCT = 75.0
LEVELS = ("full", "light", "effects")


def shed(cfg: Dict[str, Any], level: int) -> Dict[str, Any]:
    """The filter setting for a budget level (0 = the player's own)."""
    if level <= 0:
        return cfg
    sharpen = cfg.get("sharpen", "none")
    if level >= 2:
        sharpen = "none"
    elif sharpen == "dls":
        sharpen = "cas"
    return {**cfg, "sharpen": sharpen, "aa": "none"}


class FilterBudget:
    def __init__(self, clock: Callable[[], float] = time.monotonic,
                 journal: Optional[Callable[..., None]] = None) -> None:
        self.clock = clock
        self.journal = journal
        self.app: Any = None
        self.level = 0
        self.starved_since: Optional[float] = None
        self.idle_since: Optional[float] = None

    def tick(self, *, app: Any, active: bool, gpu_busy: Optional[float], starved: bool) -> int:
        """active: a game with generation on and filters to shed (not Quality)."""
        now = self.clock()
        if app != self.app:
            self.app, self.level = app, 0
            self.starved_since = self.idle_since = None
        if not active:
            self.level = 0
        if not active or not isinstance(gpu_busy, (int, float)):
            self.starved_since = self.idle_since = None
            return self.level if active else 0
        if starved and gpu_busy >= BUSY_PCT and self.level < len(LEVELS) - 1:
            self.starved_since = self.starved_since if self.starved_since is not None else now
            if now - self.starved_since >= SHED_S:
                self._set(self.level + 1, "gpu-starved", gpu_busy)
        else:
            self.starved_since = None
        if self.level and gpu_busy < IDLE_PCT:
            self.idle_since = self.idle_since if self.idle_since is not None else now
            if now - self.idle_since >= BACK_S:
                self._set(self.level - 1, "gpu-free", gpu_busy)
        else:
            self.idle_since = None
        return self.level

    def _set(self, level: int, why: str, gpu_busy: float) -> None:
        self.level = level
        self.starved_since = self.idle_since = None
        if self.journal:
            try:
                self.journal("filter-budget", level=LEVELS[level], why=why, gpu_busy=round(gpu_busy, 1))
            except Exception:
                pass

    def status(self) -> Dict[str, Any]:
        return {"level": LEVELS[self.level]}
