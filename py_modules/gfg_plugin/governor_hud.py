"""In-game HUD: MangoHud config + a one-line Governor status file.

MangoHud is already shipped as a managed Vulkan layer.  The HUD shows MangoHud's
own presented-FPS/frametime plus one ``exec`` line fed from a status file the
Governor service keeps current.  Whether MangoHud re-runs ``exec`` at a useful
cadence is unverified and must be confirmed on a Deck (see known limitations).
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

from .governor_battery import format_minutes

PRESETS = ("minimal", "standard", "detailed")
POSITIONS = ("top-left", "top-right", "bottom-left", "bottom-right")
HUD_DIRNAME = "hud"
STATUS_FILENAME = "status.txt"

_STATE_WORD = {
    "LOCKED": "locked", "OPTIMIZE_POWER": "saving power", "GUARD": "guard",
    "APPLY": "testing", "PROBE": "measuring", "PLAN": "measuring",
    "OBSERVE_ONLY": "observing", "PAUSED": "paused", "DISABLED": "off",
}


def normalize(preset: Any, position: Any) -> tuple[str, str]:
    preset = str(preset or "standard").lower()
    position = str(position or "top-right").lower()
    return (preset if preset in PRESETS else "standard",
            position if position in POSITIONS else "top-right")


def status_path(config_dir: Path) -> Path:
    return Path(config_dir) / HUD_DIRNAME / STATUS_FILENAME


def active_config_path(config_dir: Path) -> Path:
    """The file the launch wrapper looks for; present only while the HUD is on."""
    return Path(config_dir) / HUD_DIRNAME / "active.conf"


def _fmt_multiplier(value: float) -> str:
    """Nearest quarter step: 2.01 -> 2, 1.46 -> 1.5, 1.76 -> 1.75."""
    q = round(float(value) * 4) / 4
    return str(int(q)) if q == int(q) else f"{q:g}"


_EFFORT_SHORT = {"easy": "easy", "medium": "med", "hard": "hard", "nightmare": "nightmare"}


def status_line(status: Dict[str, Any], preset: str = "standard") -> str:
    """Compact: ``x2 45>90 sc100 9W 2h05 med`` (two spaces between fields)."""
    if not status.get("enabled"):
        return "GFG off"
    tel = status.get("telemetry") or {}
    tel = tel.get("summary") or tel  # service stores {"snapshot", "summary"}
    real = (tel.get("real") or {}).get("median")
    out = (tel.get("output") or {}).get("median")
    mult = (tel.get("latest") or {}).get("effective_multiplier")
    parts = [f"x{_fmt_multiplier(mult)}" if mult else "GFG"]
    if real is not None and out is not None:
        parts.append(f"{round(real)}>{round(out)}")
    if preset == "minimal":
        return "  ".join(parts)
    point = status.get("active_point") or {}
    parts.append(f"sc{int(point.get('render_scale_pct', 100))}")
    power = status.get("power") or {}
    tdp = power.get("observed_tdp_w")
    if tdp is None:
        tdp = power.get("current_w")
    parts.append(f"{round(tdp)}W" if tdp is not None else "TDPn/a")
    left = format_minutes((status.get("battery") or {}).get("minutes_left"))
    if left:
        parts.append(left)
    effort = (status.get("effort") or {}).get("level")
    if effort:
        parts.append(_EFFORT_SHORT[effort])
    if preset == "detailed":
        parts.append(_STATE_WORD.get(str(status.get("state")), "on"))
    return "  ".join(parts)


def mangohud_config(preset: str, position: str, status_file: Path) -> str:
    """Compact horizontal bar.  No CPU load; GPU only in Detailed."""
    preset, position = normalize(preset, position)
    lines = [
        f"position={position}", "legacy_layout=0", "horizontal", "background_alpha=0.4",
        "font_size=18", "round_corners=6", "text_color=FFFFFF",
        "fps", "frametime", "fps_color_change=0", "no_display=0",
    ]
    if preset == "detailed":
        lines += ["gpu_stats", "gpu_power"]
    lines.append(f"exec=cat {status_file}")
    return "\n".join(lines) + "\n"


def _atomic(path: Path, text: str) -> bool:
    """Write only on change.  Returns True if the file was rewritten."""
    try:
        if path.read_text(encoding="utf-8") == text:
            return False
    except OSError:
        pass
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.chmod(tmp, 0o644)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    return True


class HudWriter:
    def __init__(self, config_dir: Path) -> None:
        self.config_dir = Path(config_dir)

    def activate(self, preset: str, position: str) -> Path:
        path = active_config_path(self.config_dir)
        _atomic(path, mangohud_config(preset, position, status_path(self.config_dir)))
        return path

    def deactivate(self) -> None:
        try:
            active_config_path(self.config_dir).unlink()
        except FileNotFoundError:
            pass

    def write_status(self, status: Dict[str, Any], preset: str = "standard") -> bool:
        return _atomic(status_path(self.config_dir), status_line(status, preset) + "\n")
