"""Playtime target: "I want to play for 3 hours" turned into an APU power ceiling.

The battery holds ``energy`` Wh.  To last ``remaining`` hours the whole Deck may draw
``energy / remaining`` W on average.  The APU is the part GFG controls; the rest (screen, memory,
fan, Wi-Fi) is measured as battery discharge minus APU draw.  So the APU may take

    cap = energy * (1 - RESERVE) / remaining_h - others_w

and the Governor's budget search gets that as its ceiling: it keeps the game smooth inside it by
trading generated-frame ratio for watts, exactly as it does at its normal ceiling.  A target the
battery cannot reach even at the lowest TDP is reported as ``tight`` with the time it *can* reach.

**Playable first.**  A heavy game at the battery's ceiling can sink to 10 real frames shown as 30
(field report 1.4.0: 6 W) — a number on paper, unplayable in the hand.  ``playable_w`` is the
lowest power at which this game keeps its real-frame floor; the Governor learns it per game when
the ceiling starves the game, and the ceiling never goes below it.  A target that needs less is
reported as ``limited`` with the time that is realistic while staying playable.

**Choices from the game, not a fixed scale.**  ``options`` offers what this game can actually do
on this charge: a few steps between the current pace and the longest playable time ("Max").

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
OPTION_STEPS = (1.15, 1.3, 1.5)    # longer than the current pace by this much
OPTION_ROUND_MIN = 10


class PlaytimePlanner:
    def __init__(self) -> None:
        self.target_h: Optional[float] = None
        self.deadline: Optional[float] = None     # wall clock (time.time) the battery must reach
        self.others_w: Optional[float] = None
        self._cap: Optional[float] = None          # smoothed raw ceiling
        self.cap_w: Optional[float] = None         # the ceiling in force (stepped, hysteresis)
        self.playable_w: Optional[float] = None    # this game's lowest playable power (learned)
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
    def options(self, *, battery: Dict[str, Any], min_w: float) -> Optional[Dict[str, Any]]:
        """Targets this game can reach on this charge, in minutes, plus the current pace."""
        energy_uwh = battery.get("energy_uwh")
        battery_w = battery.get("power_uw")
        if (not battery.get("available") or not battery.get("discharging")
                or not isinstance(energy_uwh, (int, float)) or energy_uwh <= 0
                or not isinstance(battery_w, (int, float)) or battery_w <= 500_000):
            return None
        energy_wh = float(energy_uwh) / 1e6
        pace_min = energy_wh / (float(battery_w) / 1e6) * 60.0
        others = self.others_w if self.others_w is not None else OTHERS_DEFAULT_W
        floor = max(min_w, self.playable_w or 0.0)
        max_min = energy_wh * (1.0 - RESERVE) / (floor + others) * 60.0
        step = OPTION_ROUND_MIN
        choices = []
        for k in OPTION_STEPS:
            m = int(pace_min * k // step * step)
            if pace_min + step <= m < max_min - step and m not in choices:
                choices.append(m)
        top = int(max_min // step * step)
        if top > pace_min + step and top not in choices:
            choices.append(top)
        return {"pace_min": int(pace_min), "max_min": top, "choices": choices}

    def update(self, now: float, *, battery: Dict[str, Any], apu_draw_w: Optional[float],
               min_w: float, max_w: float) -> Dict[str, Any]:
        if self.deadline is None:
            self._learn_others(battery, apu_draw_w)
            self.last = {"active": False, "options": self.options(battery=battery, min_w=min_w),
                         "playable_w": self.playable_w}
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
        battery_w = self._learn_others(battery, apu_draw_w)
        others_w = self.others_w if self.others_w is not None else OTHERS_DEFAULT_W
        floor_w = max(min_w, min(max_w, self.playable_w)) if self.playable_w else min_w
        energy_wh = float(energy_uwh) / 1e6
        allowed_w = energy_wh * (1.0 - RESERVE) / (remaining_s / 3600.0)
        raw = allowed_w - others_w
        self._cap = raw if self._cap is None else self._cap + CAP_ALPHA * (raw - self._cap)
        wanted = max(floor_w, min(max_w, round(self._cap / STEP_W) * STEP_W))
        if self.cap_w is None or abs(wanted - self.cap_w) >= HYSTERESIS_W:
            self.cap_w = wanted
        reachable_min = int(energy_wh * (1.0 - RESERVE) / (floor_w + others_w) * 60.0)
        forecast_min = int(energy_wh / battery_w * 60.0) if battery_w else None
        if raw < floor_w and floor_w > min_w + 1e-6:
            state = "limited"        # possible only by making the game unplayable: it is not done
        elif raw < min_w:
            state = "tight"          # even the lowest TDP cannot last that long
        elif raw >= max_w:
            state = "on-track"       # no limit needed
        else:
            state = "holding"
        self.last = {**out, "state": state, "cap_w": self.cap_w if state != "on-track" else None,
                     "allowed_w": round(allowed_w, 1), "others_w": round(others_w, 1),
                     "reachable_min": reachable_min, "forecast_min": forecast_min,
                     "energy_wh": round(energy_wh, 1), "playable_w": self.playable_w,
                     "options": self.options(battery=battery, min_w=min_w)}
        return self.last

    def _learn_others(self, battery: Dict[str, Any], apu_draw_w: Optional[float]) -> Optional[float]:
        """Rest-of-Deck draw (battery drain minus APU), smoothed; returns the battery draw in W."""
        if not battery.get("discharging"):
            return None
        battery_w = battery.get("power_uw")
        battery_w = float(battery_w) / 1e6 if isinstance(battery_w, (int, float)) and battery_w > 500_000 else None
        if battery_w is not None and isinstance(apu_draw_w, (int, float)) and 0 < apu_draw_w < battery_w:
            others = battery_w - float(apu_draw_w)
            self.others_w = others if self.others_w is None else self.others_w + OTHERS_ALPHA * (others - self.others_w)
        return battery_w

    def raise_playable(self, watts: float, max_w: float) -> float:
        """The ceiling starved the game: it needs at least ``watts`` to stay playable."""
        self.playable_w = round(min(max_w, max(float(watts), self.playable_w or 0.0)), 1)
        self._cap = max(self._cap or 0.0, self.playable_w)
        self.cap_w = max(self.cap_w or 0.0, self.playable_w)
        return self.playable_w
