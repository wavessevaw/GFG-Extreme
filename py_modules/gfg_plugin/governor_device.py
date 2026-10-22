"""Device and display-mode detection for the Governor target policy.

Targets (output FPS):

* Steam Deck OLED (DMI ``Galileo``), handheld ........ 90
* Steam Deck LCD  (DMI ``Jupiter``), handheld ........ 60 (an unlocked panel: its running 61-80 Hz)
* Any device docked to an external display ........... 60

Unknown hardware falls back to the internal panel's highest valid refresh rate.  60 FPS is a
target only on the LCD and in the dock: on a 90 Hz panel (OLED) the target stays 90 even when
the panel reports a lower refresh, and Autopilot's reduced goal is 45 (half the panel, even
frame times), never 60.  On the LCD the target still follows a lower running refresh.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, Optional

DMI_ROOT = Path("/sys/class/dmi/id")
_MODELS = {"galileo": "oled", "jupiter": "lcd"}
TARGET_OLED = 90
TARGET_LCD = 60
TARGET_DOCK = 60
LCD_UNLOCKED_MAX_HZ = 80


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
    if (not external and model == "lcd" and isinstance(current_hz, (int, float)) and not isinstance(current_hz, bool)
            and TARGET_LCD < current_hz <= LCD_UNLOCKED_MAX_HZ):
        # Some LCD Decks run their panel unlocked above 60 Hz (often 70-75): the running refresh
        # is the target then (user, 3.1.0).
        hz = int(round(current_hz))
        return {"target": hz, "mode": "lcd", "reason": f"steam-deck-lcd-unlocked-{hz}hz"}
    if (not external and policy["target"] < TARGET_OLED
            and isinstance(current_hz, (int, float)) and not isinstance(current_hz, bool)
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


def external_display_connected(drm_root: Path = Path("/sys/class/drm")) -> bool:
    """True while a DisplayPort or HDMI connector reports a connected display (the dock)."""
    try:
        connectors = sorted(Path(drm_root).glob("card*-*"))
    except OSError:
        return False
    for connector in connectors:
        name = connector.name.split("-", 1)[-1]
        if not name.startswith(("DP", "HDMI")):
            continue
        try:
            if (connector / "status").read_text(encoding="utf-8").strip() == "connected":
                return True
        except (OSError, UnicodeError):
            continue
    return False
