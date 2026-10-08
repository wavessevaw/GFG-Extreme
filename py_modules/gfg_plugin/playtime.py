"""Playtime target: "I want to play for 3 hours" turned into an APU power ceiling.

The battery holds ``energy`` Wh.  To last ``remaining`` hours the whole Deck may draw
``energy / remaining`` W on average.  The APU is the part GFG controls; the rest (screen, memory,
fan, Wi-Fi) is measured as battery discharge minus APU draw.  So the APU may take

    cap = energy * (1 - RESERVE) / remaining_h - others_w

and the Governor's budget search gets that as its ceiling: it keeps the game smooth inside it by
trading generated-frame ratio for watts, exactly as it does at its normal ceiling.  A target the
battery cannot reach even at the lowest TDP is reported as ``tight`` with the time it *can* reach.

Pure logic with an injected clock.  The ceiling moves in ``STEP_W`` steps and only when the
smoothed value has moved by more than ``HYSTERESIS_W``, so the TDP does not wander every second.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

RESERVE = 0.05            # keep 5 % of the energy in hand: the battery estimate drifts at the end
OTHERS_DEFAULT_W = 4.5    # Deck without the APU (screen at mid brightness, memory, fan) until measured
OTHERS_ALPHA = 0.05       # ~20 s smoothing of the measured rest-of-Deck draw
CAP_ALPHA = 0.1
STEP_W = 0.5
HYSTERESIS_W = 0.6
MIN_REMAINING_S = 60.0
CHOICES_H = (1.5, 2.0, 2.5, 3.0, 4.0, 5.0)


class PlaytimePlanner:
    def __init__(self) -> None:
        self.target_h: Optional[float] = None
        self.deadline: Optional[float] = None     # wall clock (time.time) the battery must reach
        self.others_w: Optional[float] = None
        self._cap: Optional[float] = None          # smoothed raw ceiling
        self.cap_w: Optional[float] = None         # the ceiling in force (stepped, hysteresis)
        self.last: Dict[str, Any] = {"active": False}

    # ------------------------------------------------------------------ settings
    def set_target(self, hours: Optional[float], now: float) -> None:
        if hours is None or not isinstance(hours, (int, float)) or hours <= 0:
            self.target_h = self.deadline = None
            self._cap = self.cap_w = None
            self.last = {"active": False}
            return
        self.target_h = float(hours)
        self.deadline = now + float(hours) * 3600.0
        self._cap = self.cap_w = None

    def restore(self, target_h: Optional[float], deadline: Optional[float], now: float) -> None:
        """A saved target survives a plugin restart while its deadline is still ahead."""
        if isinstance(target_h, (int, float)) and isinstance(deadline, (int, float)) and deadline > now + MIN_REMAINING_S:
            self.target_h, self.deadline = float(target_h), float(deadline)

    # ------------------------------------------------------------------ per Governor step
    def update(self, now: float, *, battery: Dict[str, Any], apu_draw_w: Optional[float],
               min_w: float, max_w: float) -> Dict[str, Any]:
        if self.deadline is None:
            self.last = {"active": False}
            return self.last
        remaining_s = self.deadline - now
        out: Dict[str, Any] = {"active": True, "target_h": self.target_h, "deadline": self.deadline,
                               "remaining_min": max(0, int(remaining_s // 60))}
        if remaining_s <= MIN_REMAINING_S:
            self.cap_w = None
            self.last = {**out, "state": "reached", "cap_w": None}
            return self.last
        energy_uwh = battery.get("energy_uwh")
        if not battery.get("available") or not isinstance(energy_uwh, (int, float)) or energy_uwh <= 0:
            self.cap_w = None
            self.last = {**out, "state": "no-battery", "cap_w": None}
            return self.last
        if not battery.get("discharging"):
            self.cap_w = None
            self.last = {**out, "state": "charging", "cap_w": None}
            return self.last
        battery_w = battery.get("power_uw")
        battery_w = float(battery_w) / 1e6 if isinstance(battery_w, (int, float)) and battery_w > 500_000 else None
        if battery_w is not None and isinstance(apu_draw_w, (int, float)) and 0 < apu_draw_w < battery_w:
            others = battery_w - float(apu_draw_w)
            self.others_w = others if self.others_w is None else self.others_w + OTHERS_ALPHA * (others - self.others_w)
        others_w = self.others_w if self.others_w is not None else OTHERS_DEFAULT_W
        energy_wh = float(energy_uwh) / 1e6
        allowed_w = energy_wh * (1.0 - RESERVE) / (remaining_s / 3600.0)
        raw = allowed_w - others_w
        self._cap = raw if self._cap is None else self._cap + CAP_ALPHA * (raw - self._cap)
        wanted = max(min_w, min(max_w, round(self._cap / STEP_W) * STEP_W))
        if self.cap_w is None or abs(wanted - self.cap_w) >= HYSTERESIS_W:
            self.cap_w = wanted
        reachable_min = int(energy_wh * (1.0 - RESERVE) / (min_w + others_w) * 60.0)
        forecast_min = int(energy_wh / battery_w * 60.0) if battery_w else None
        if raw < min_w:
            state = "tight"          # even the lowest TDP cannot last that long
        elif raw >= max_w:
            state = "on-track"       # no limit needed
        else:
            state = "holding"
        self.last = {**out, "state": state, "cap_w": self.cap_w if state != "on-track" else None,
                     "allowed_w": round(allowed_w, 1), "others_w": round(others_w, 1),
                     "reachable_min": reachable_min, "forecast_min": forecast_min,
                     "energy_wh": round(energy_wh, 1)}
        return self.last
