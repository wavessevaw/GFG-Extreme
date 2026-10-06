"""Battery state and time-to-empty from sysfs (smoothed, never guessed)."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

POWER_SUPPLY = Path("/sys/class/power_supply")


def _read(path: Path) -> Optional[str]:
    try:
        return path.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeError):
        return None


def _num(path: Path) -> Optional[float]:
    value = _read(path)
    try:
        return float(value) if value is not None else None
    except ValueError:
        return None


def read_battery(root: Path = POWER_SUPPLY) -> Dict[str, Any]:
    """Return ``{available, percent, discharging, energy_uwh, power_uw}``."""
    try:
        candidates = sorted(root.glob("BAT*"))
    except OSError:
        candidates = []
    for bat in candidates:
        energy = _num(bat / "energy_now")
        power = _num(bat / "power_now")
        if energy is None:  # charge-based batteries report charge_now/current_now
            charge, voltage, current = _num(bat / "charge_now"), _num(bat / "voltage_now"), _num(bat / "current_now")
            if charge is not None and voltage is not None:
                energy = charge * voltage / 1_000_000.0
                power = abs(current) * voltage / 1_000_000.0 if current is not None else None
        if energy is None:
            continue
        return {
            "available": True,
            "percent": _num(bat / "capacity"),
            "discharging": (_read(bat / "status") or "").lower() == "discharging",
            "energy_uwh": energy,
            "power_uw": abs(power) if power is not None else None,
        }
    return {"available": False}


class BatteryEstimator:
    """Time to empty from an EMA of the discharge power, so it doesn't jitter."""

    ALPHA = 0.08

    def __init__(self) -> None:
        self._ema: Optional[float] = None

    def update(self, battery: Dict[str, Any]) -> Dict[str, Any]:
        if not battery.get("available") or not battery.get("discharging"):
            self._ema = None
            return {**battery, "minutes_left": None}
        power = battery.get("power_uw")
        if power and power > 0:
            self._ema = power if self._ema is None else self._ema + self.ALPHA * (power - self._ema)
        minutes = None
        if self._ema and self._ema > 500_000:  # ignore <0.5 W readings: noise
            minutes = int(round(battery["energy_uwh"] / self._ema * 60.0))
        return {**battery, "minutes_left": minutes}


def format_minutes(minutes: Optional[int]) -> Optional[str]:
    if minutes is None or minutes < 0:
        return None
    return f"{minutes // 60}h{minutes % 60:02d}" if minutes >= 60 else f"{minutes}m"
