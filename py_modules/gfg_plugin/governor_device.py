"""Device and display-mode detection for the Governor target policy.

Targets (output FPS):

* Steam Deck OLED (DMI ``Galileo``), handheld ........ 90
* Steam Deck LCD  (DMI ``Jupiter``), handheld ........ 60 (panel is 60 Hz max)
* Any device docked to an external display ........... 60

Unknown hardware falls back to the internal panel's highest valid refresh rate.  On the internal
panel the target never exceeds the refresh rate it actually runs at, when that is readable (an
OLED set to 60 Hz cannot show 90 FPS).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, Optional

DMI_ROOT = Path("/sys/class/dmi/id")
_MODELS = {"galileo": "oled", "jupiter": "lcd"}
TARGET_OLED = 90
TARGET_LCD = 60
TARGET_DOCK = 60


def detect_model(dmi_root: Path = DMI_ROOT) -> Dict[str, str]:
    """Return ``{"model": "oled|lcd|unknown", "product": <dmi product name>}``."""
    product = ""
    for name in ("product_name", "board_name"):
        try:
            product = (Path(dmi_root) / name).read_text(encoding="utf-8").strip()
        except (OSError, UnicodeError):
            continue
        if product:
            break
    return {"model": _MODELS.get(product.casefold(), "unknown"), "product": product}


def target_for(
    model: str, *, external: bool, valid_rates: Optional[Iterable[Any]] = None,
    current_hz: Optional[Any] = None,
) -> Dict[str, Any]:
    """Pick the output-FPS target and say why (shown verbatim in the UI)."""
    policy = _device_target(model, external=external, valid_rates=valid_rates)
    if (not external and isinstance(current_hz, (int, float)) and not isinstance(current_hz, bool)
            and 20 <= current_hz < policy["target"]):
        hz = int(round(current_hz))
        return {"target": hz, "mode": policy["mode"], "reason": f"panel-running-{hz}hz"}
    return policy


def _device_target(
    model: str, *, external: bool, valid_rates: Optional[Iterable[Any]] = None
) -> Dict[str, Any]:
    if external:
        return {"target": TARGET_DOCK, "mode": "dock", "reason": "external-display"}
    if model == "oled":
        return {"target": TARGET_OLED, "mode": "oled", "reason": "steam-deck-oled-90hz"}
    if model == "lcd":
        return {"target": TARGET_LCD, "mode": "lcd", "reason": "steam-deck-lcd-60hz"}
    rates = [float(r) for r in (valid_rates or []) if isinstance(r, (int, float)) and 20 <= float(r) <= 240]
    if rates and max(rates) >= 90:
        return {"target": TARGET_OLED, "mode": "oled", "reason": "unknown-device-90hz-panel"}
    return {"target": TARGET_LCD, "mode": "lcd", "reason": "unknown-device-default-60"}
