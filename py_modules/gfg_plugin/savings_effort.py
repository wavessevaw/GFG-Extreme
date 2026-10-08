"""Battery-mode savings *effort*, never a promised number of hours.

Power presets are soft budgets. A source-frame collapse overrides them; generated
FPS must never masquerade as evidence of playability. The controller owns TDP:
this policy only supplies limits and a bounded, hysteretic safety floor.
"""
from __future__ import annotations

import math
from typing import Any, Dict, Optional

LEVELS = ("off", "light", "medium", "hard")
# (normal APU ceiling, minimum search watts). A hard setting may be relaxed by
# real gameplay evidence. "Off" means no extra ceiling, *not* an unsafe 6 W floor.
PRESETS: Dict[str, tuple[Optional[float], float]] = {
    "off": (None, 6.0),
    "light": (14.0, 10.0),
    "medium": (12.0, 9.0),
    "hard": (11.0, 9.0),
}
UNPLAYABLE_REAL_FPS = 24.0
UNPLAYABLE_OUTPUT_RATIO = 0.80
UNPLAYABLE_HOLD_S = 4.0
POWER_BINDING_MARGIN_W = 1.5
RECOVERY_STEP_W = 2.0


class SavingsEffort:
    """Pure per-game policy, independent of the game profile and output FPS HUD."""

    def __init__(self) -> None:
        self.level = "off"
        self.game = ""
        self.learned_floor_w: Optional[float] = None
        self._bad_since: Optional[float] = None
        self._last_bad_at: Optional[float] = None

    def configure(self, level: str, game: str, learned_floor_w: Optional[float] = None) -> None:
        level = level if level in PRESETS else "off"
        game = str(game or "")
        if level != self.level or game != self.game:
            self.level, self.game = level, game
            self._bad_since = self._last_bad_at = None
            self.learned_floor_w = None
        if isinstance(learned_floor_w, (int, float)) and math.isfinite(learned_floor_w) and learned_floor_w > 0:
            self.learned_floor_w = max(self.learned_floor_w or 0.0, float(learned_floor_w))

    def limits(self, hardware_min_w: float, normal_max_w: float) -> Dict[str, Any]:
        requested_cap, requested_floor = PRESETS[self.level]
        floor = min(normal_max_w, max(hardware_min_w, requested_floor, self.learned_floor_w or 0.0))
        quality_limited = requested_cap is not None and floor > requested_cap
        # Once the game proves it needs more, the artificial ceiling may not
        # obstruct recovery. The Governor can still use its normal emergency path.
        cap = None if quality_limited else requested_cap
        return {"level": self.level, "minimum_w": round(floor, 1),
                "cap_w": min(normal_max_w, cap) if cap is not None else None,
                "quality_limited": quality_limited,
                "learned_floor_w": self.learned_floor_w}

    def observe(self, now: float, *, real_fps: Optional[float],
                output_fps: Optional[float], target_fps: Optional[float],
                tdp_w: Optional[float], draw_w: Optional[float],
                valid: bool, normal_max_w: float) -> bool:
        """Escalate only on consecutive real+output failures with a binding cap.

        Return True if the saved safety floor has increased. Never infer power
        shortage from a menu, a stale FPS value, or a game using far less than
        its power allowance. The caller supplies "valid" for these conditions.
        """
        values = (real_fps, output_fps, target_fps, tdp_w)
        sane = valid and all(isinstance(x, (int, float)) and math.isfinite(x) and x > 0
                             for x in values)
        binding = draw_w is None or (
            isinstance(draw_w, (int, float)) and math.isfinite(draw_w)
            and draw_w >= float(tdp_w or 0) - POWER_BINDING_MARGIN_W)
        bad = sane and binding and real_fps < UNPLAYABLE_REAL_FPS
        if self.level == "off":
            self._bad_since = self._last_bad_at = None
            return False
        if not bad:
            self._bad_since = self._last_bad_at = None
            return False
        if self._last_bad_at is None or now < self._last_bad_at or now - self._last_bad_at > 2.5:
            self._bad_since = now
        self._last_bad_at = now
        if now - self._bad_since < UNPLAYABLE_HOLD_S:
            return False
        self._bad_since = self._last_bad_at = None
        old = self.learned_floor_w or 0.0
        # Allow TDP to recover *past* a failed savings ceiling; never lift
        # beyond the device's normal limit based solely on this quick check.
        self.learned_floor_w = round(min(normal_max_w, max(old + 1.0, float(tdp_w) + RECOVERY_STEP_W)), 1)
        return self.learned_floor_w > old + 0.01

def hard_refresh_target(level: str, model: str, external: bool) -> Optional[int]:
    """Only Hard in Battery requests a display rate; never touch docked panels."""
    if level != "hard" or external:
        return None
    return {"oled": 60, "lcd": 45}.get(model)
