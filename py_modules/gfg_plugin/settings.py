"""GFG Extreme 3.0 settings: one JSON file, validated on every load and change.

Profiles: "default" applies to every game without its own profile; "app:<Steam app id>" is a
game's own profile, made when the player chooses "only this game" for the running game.
A profile holds what the player picks per game: frame generation, the power objective and
the filters. HUD and Autopilot preference are global.
"""
from __future__ import annotations

import copy
import time
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple

from . import filters
from .user_files import read_json, write_json_atomic

SCHEMA = 3
FG_MODES = ("off", "auto", "x2", "x3", "x3.75", "custom")
TELEMETRY_LEVELS = ("minimal", "standard", "debug")
OBJECTIVES = ("autopilot", "battery", "balanced", "quality")
AUTOPILOT_PREFERENCES = ("auto", "battery", "smoothness")
HUD_POSITIONS = ("top-left", "top-right", "bottom-left", "bottom-right")
HUD_DETAILS = ("minimal", "standard")
BASE_FPS_RANGE = (20, 90)
DEFAULT_PROFILE = "default"


def default_profile() -> Dict[str, Any]:
    return {"name": "Default", "fg": "auto", "base_fps": 45, "objective": "autopilot",
            "filters": dict(filters.OFF)}


def defaults() -> Dict[str, Any]:
    return {
        "schema": SCHEMA,
        "profiles": {DEFAULT_PROFILE: default_profile()},
        "hud": {"enabled": True, "position": "top-right", "detail": "standard"},
        "autopilot": {"preference": "auto"},
        "power": {"enabled": True, "split": True, "gpu_clock": True},
        "engine": {"hdr": True, "hdr_output": True, "above_x3": False, "boost": False, "boost_mult": 1.5},
        "telemetry": {"level": "standard"},
        "migrated_from": None,
    }


def profile_key(app_id: Any) -> Optional[str]:
    try:
        app = int(app_id)
    except (TypeError, ValueError):
        return None
    return f"app:{app}" if app > 0 and app != 769 else None


def _int_in(value: Any, low: int, high: int, default: int) -> int:
    try:
        v = int(value)
    except (TypeError, ValueError):
        return default
    return min(high, max(low, v))


def normalize_profile(raw: Any, name: str = "Default") -> Dict[str, Any]:
    raw = raw if isinstance(raw, dict) else {}
    base = default_profile()
    return {
        "name": str(raw.get("name") or name)[:80],
        # Dash offers only Off; every other stored choice now means the mode picks the multiplier.
        "fg": "off" if raw.get("fg") == "off" else "auto",
        "base_fps": _int_in(raw.get("base_fps"), *BASE_FPS_RANGE, base["base_fps"]),
        "objective": raw.get("objective") if raw.get("objective") in OBJECTIVES else base["objective"],
        "filters": filters.normalize(raw.get("filters")),
    }


def normalize(raw: Any) -> Dict[str, Any]:
    raw = raw if isinstance(raw, dict) else {}
    out = defaults()
    profiles = raw.get("profiles") if isinstance(raw.get("profiles"), dict) else {}
    for key, value in profiles.items():
        if key == DEFAULT_PROFILE or (isinstance(key, str) and key.startswith("app:") and key[4:].isdigit()):
            out["profiles"][key] = normalize_profile(value, "Default" if key == DEFAULT_PROFILE else key)
    hud = raw.get("hud") if isinstance(raw.get("hud"), dict) else {}
    out["hud"] = {
        "enabled": bool(hud.get("enabled", True)),
        "position": hud.get("position") if hud.get("position") in HUD_POSITIONS else "top-right",
        "detail": hud.get("detail") if hud.get("detail") in HUD_DETAILS else "standard",
    }
    ap = raw.get("autopilot") if isinstance(raw.get("autopilot"), dict) else {}
    out["autopilot"] = {"preference": ap.get("preference") if ap.get("preference") in AUTOPILOT_PREFERENCES else "auto"}
    power = raw.get("power") if isinstance(raw.get("power"), dict) else {}
    out["power"] = {"enabled": bool(power.get("enabled", True)), "split": bool(power.get("split", True)),
                    "gpu_clock": bool(power.get("gpu_clock", True))}
    eng = raw.get("engine") if isinstance(raw.get("engine"), dict) else {}
    out["engine"] = {"hdr": bool(eng.get("hdr", True)), "hdr_output": bool(eng.get("hdr_output", True)),
                     # Above x3 (user, 3.1.1): x3.75 plays badly, so it is unlocked only here.
                     "above_x3": bool(eng.get("above_x3", False)),
                     # Boost (user, 3.1.1): a camera turn of ~1 s gets x1.25-x1.75 until the stick rests.
                     "boost": bool(eng.get("boost", False)),
                     "boost_mult": eng.get("boost_mult") if eng.get("boost_mult") in (1.25, 1.5, 1.75) else 1.5}
    tel = raw.get("telemetry") if isinstance(raw.get("telemetry"), dict) else {}
    out["telemetry"] = {"level": tel.get("level") if tel.get("level") in TELEMETRY_LEVELS else "standard"}
    out["migrated_from"] = raw.get("migrated_from") if isinstance(raw.get("migrated_from"), (str, type(None))) else None
    return out


class Settings:
    def __init__(self, path: Path, owner: Optional[Tuple[int, int]] = None,
                 clock: Callable[[], float] = time.time) -> None:
        self.path = Path(path)
        self.owner = owner
        self.clock = clock
        self.exists = self.path.exists()
        self.data = normalize(read_json(self.path, {}))

    def save(self) -> None:
        self.rev = getattr(self, "rev", 0) + 1   # the service re-runs its idle pipeline on a change
        write_json_atomic(self.path, self.data, self.owner)
        self.exists = True

    def replace(self, data: Dict[str, Any]) -> None:
        self.data = normalize(data)
        self.save()

    # ---------------------------------------------------------------- profiles
    def profile_for(self, app_id: Any) -> Tuple[str, Dict[str, Any]]:
        key = profile_key(app_id)
        if key and key in self.data["profiles"]:
            return key, copy.deepcopy(self.data["profiles"][key])
        return DEFAULT_PROFILE, copy.deepcopy(self.data["profiles"][DEFAULT_PROFILE])

    def update_profile(self, key: str, changes: Dict[str, Any]) -> Dict[str, Any]:
        if key not in self.data["profiles"]:
            raise KeyError(key)
        merged = {**self.data["profiles"][key], **changes}
        self.data["profiles"][key] = normalize_profile(merged, self.data["profiles"][key]["name"])
        self.save()
        return copy.deepcopy(self.data["profiles"][key])

    def make_game_profile(self, app_id: Any, name: str = "") -> str:
        key = profile_key(app_id)
        if key is None:
            raise ValueError("no game is running")
        if key not in self.data["profiles"]:
            base = copy.deepcopy(self.data["profiles"][DEFAULT_PROFILE])
            base["name"] = name or key
            self.data["profiles"][key] = normalize_profile(base, base["name"])
            self.save()
        return key

    def drop_game_profile(self, app_id: Any) -> bool:
        key = profile_key(app_id)
        if key and self.data["profiles"].pop(key, None) is not None:
            self.save()
            return True
        return False

    # ---------------------------------------------------------------- globals
    def set_section(self, section: str, changes: Dict[str, Any]) -> Dict[str, Any]:
        if section not in ("hud", "autopilot", "power", "telemetry", "engine"):
            raise KeyError(section)
        candidate = copy.deepcopy(self.data)
        candidate[section] = {**candidate[section], **changes}
        self.data = normalize(candidate)
        self.save()
        return copy.deepcopy(self.data[section])
