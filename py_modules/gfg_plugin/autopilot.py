"""Autopilot: picks the power objective, and nothing that KEDAVRA's own Auto already does.

KEDAVRA Auto picks the multiplier and the base cap from the game's frame rate. Autopilot
decides only how much power that may cost:

  preference "smoothness"  -> Quality (no TDP probing; the player's TDP stays)
  preference "battery"     -> Battery
  preference "auto"        -> Quality on external power, Battery below 20 % battery (back above
                              25 %), Balanced otherwise

A hot Deck (85 C and above) never runs Quality: Balanced, so the Governor may lower the TDP.
A choice holds at least 60 s, so a battery reading at the threshold does not flap.

Battery in delegated Auto also lowers the base cap to 30 (x3 at 90 Hz, x2 at 60 Hz): the
game renders fewer frames, generation fills the refresh. A fixed x2/x3 or Custom cap chosen by
the player is never changed.
"""
from __future__ import annotations

import time
from typing import Any, Callable, Dict, Optional

DWELL_S = 60.0
LOW_BATTERY = 20.0
BATTERY_RECOVER = 25.0
HOT_C = 85.0
BATTERY_CAP = 30


class Autopilot:
    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self.clock = clock
        self.objective: Optional[str] = None
        self.reason = ""
        self.changed_at = -1e9
        self.low_battery = False
        self.thermal_limited = False
        self.cool_since = None

    def _wish(self, preference: str, power: Dict[str, Any], temp_c: Optional[float]) -> tuple:
        pct = power.get("percent")
        if pct is not None:
            if pct < LOW_BATTERY:
                self.low_battery = True
            elif pct > BATTERY_RECOVER:
                self.low_battery = False
        if preference == "smoothness":
            wish, why = "quality", "preference: smoothness"
        elif preference == "battery":
            wish, why = "battery", "preference: battery"
        elif power.get("external_power"):
            wish, why = "quality", "on external power"
        elif self.low_battery:
            wish, why = "battery", f"battery below {LOW_BATTERY:.0f} %"
        else:
            wish, why = "balanced", "on battery"
        hot = temp_c is not None and temp_c >= HOT_C
        if hot:
            self.thermal_limited = True
            self.cool_since = None
        elif self.thermal_limited:
            if temp_c is not None and temp_c < HOT_C - 5:
                if self.cool_since is None:
                    self.cool_since = self.clock()
                if self.clock() - self.cool_since >= DWELL_S:
                    self.thermal_limited = False
            else:
                self.cool_since = None
        if wish == "quality" and self.thermal_limited:
            wish, why = "balanced", "APU thermal limit: waiting for sustained cooling"
        return wish, why, hot or preference != "auto"

    def decide(self, preference: str, power: Dict[str, Any], temp_c: Optional[float]) -> Dict[str, Any]:
        now = self.clock()
        wish, why, urgent = self._wish(preference, power, temp_c)
        # Hot, or a fixed preference: no dwell. Otherwise a choice holds 60 s.
        urgent = urgent or self.objective is None
        if wish != self.objective and (urgent or now - self.changed_at >= DWELL_S):
            self.objective, self.reason, self.changed_at = wish, why, now
        return {"objective": self.objective, "reason": self.reason}

    def reset(self) -> None:
        self.objective = None
        self.reason = ""
        self.changed_at = -1e9


def engine_request(fg: str, base_fps: int, objective: str) -> Dict[str, int]:
    """Multiplier and base cap for the engine, from the profile's frame generation choice.

    off -> 0/0; auto -> 1/0 (KEDAVRA Auto), or 1/30 under Battery; x2 -> 2/0; x3 -> 3/0;
    custom -> 1/base_fps (the game held at base_fps, generation fills the refresh).
    """
    if fg == "off":
        return {"multiplier": 0, "base_fps": 0}
    if fg == "x2":
        return {"multiplier": 2, "base_fps": 0}
    if fg == "x3":
        return {"multiplier": 3, "base_fps": 0}
    if fg == "custom":
        return {"multiplier": 1, "base_fps": int(base_fps)}
    return {"multiplier": 1, "base_fps": BATTERY_CAP if objective == "battery" else 0}
