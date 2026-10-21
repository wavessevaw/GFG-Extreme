"""Filters: the looks GFG Extreme offers and the ``kfg_post`` string the engine runs.

The filters run inside the KEDAVRA Gamescope on the frame each vblank shows, after frame
generation: real and generated frames get the same look, the motion analysis never sees
grain or sharpening, and the HUD and Steam's overlays stay unfiltered. They work with frame
generation off too, on SDR game frames. No vkBasalt layer, no game restart.

The keys are the same as GFG Extreme 2.x used for vkBasalt, so saved looks carry over.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Tuple

# key, name shown, group. Order = how the UI lists them; the engine has its own fixed order.
EFFECTS: Tuple[Tuple[str, str, str], ...] = (
    ("hdr_look", "HDR Look", "light"),
    ("clarity", "Clarity", "light"),
    ("levels_plus", "Levels Plus", "light"),
    ("curves", "Curves", "light"),
    ("vibrance", "Vibrance", "colour"),
    ("colourfulness", "Colourfulness", "colour"),
    ("technicolor", "Technicolor", "colour"),
    ("technicolor2", "Technicolor 2", "colour"),
    ("dpx", "DPX", "colour"),
    ("bleach_bypass", "Bleach Bypass", "film"),
    ("noir", "Noir", "film"),
    ("sepia", "Sepia", "film"),
    ("monochrome", "Monochrome", "film"),
    ("film_grain", "Film Grain", "film"),
    ("vignette", "Vignette", "film"),
    ("chromatic_aberration", "Chromatic Aberration", "film"),
    ("cartoon", "Cartoon", "style"),
    ("nostalgia", "Nostalgia", "style"),
    ("deband", "Deband", "clean"),
)
EFFECT_KEYS = tuple(k for k, _, _ in EFFECTS)
SHARPEN = ("none", "cas", "dls")
AA = ("none", "fxaa", "smaa")

DEFAULT_SHARPNESS = 0.4
DEFAULT_DENOISE = 0.17

OFF: Dict[str, Any] = {"effects": [], "sharpen": "none", "sharpness": DEFAULT_SHARPNESS,
                       "denoise": DEFAULT_DENOISE, "aa": "none"}

PRESETS: Tuple[Tuple[str, str, Dict[str, Any]], ...] = (
    ("off", "Off", {}),
    ("sharp", "Sharp", {"sharpen": "cas", "sharpness": 0.5}),
    ("vivid", "Vivid", {"effects": ["vibrance"], "sharpen": "cas", "sharpness": 0.35}),
    ("hdr", "HDR look", {"effects": ["hdr_look"], "sharpen": "cas", "sharpness": 0.3}),
    ("cinema", "Cinema", {"effects": ["technicolor2", "vignette"]}),
    ("noir", "Noir", {"effects": ["noir", "film_grain"]}),
    ("retro", "Retro", {"effects": ["nostalgia", "vignette"]}),
    ("smooth", "Smooth", {"sharpen": "cas", "sharpness": 0.3, "aa": "smaa"}),
)
PRESET_IDS = tuple(p for p, _, _ in PRESETS)


def _unit(value: Any, default: float) -> float:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(v):
        return default
    return round(min(1.0, max(0.0, v)), 2)


def normalize(raw: Any) -> Dict[str, Any]:
    """A valid filter setting from anything (unknown effects and values dropped)."""
    raw = raw if isinstance(raw, dict) else {}
    effects: List[str] = []
    for e in raw.get("effects") or []:
        if e in EFFECT_KEYS and e not in effects:
            effects.append(e)
    sharpen = raw.get("sharpen") if raw.get("sharpen") in SHARPEN else "none"
    aa = raw.get("aa") if raw.get("aa") in AA else "none"
    return {"effects": effects, "sharpen": sharpen, "sharpness": _unit(raw.get("sharpness"), DEFAULT_SHARPNESS),
            "denoise": _unit(raw.get("denoise"), DEFAULT_DENOISE), "aa": aa}


def preset(preset_id: str) -> Dict[str, Any]:
    for pid, _, values in PRESETS:
        if pid == preset_id:
            return normalize({**OFF, **values})
    raise ValueError(f"unknown preset {preset_id}")


def preset_of(cfg: Dict[str, Any]) -> str:
    """The preset this setting equals, or "custom"."""
    cfg = normalize(cfg)
    for pid, _, _ in PRESETS:
        p = preset(pid)
        same = (sorted(p["effects"]) == sorted(cfg["effects"]) and p["sharpen"] == cfg["sharpen"] and p["aa"] == cfg["aa"]
                and (p["sharpen"] == "none" or abs(p["sharpness"] - cfg["sharpness"]) < 0.01))
        if same:
            return pid
    return "custom"


def is_active(cfg: Dict[str, Any]) -> bool:
    cfg = normalize(cfg)
    return bool(cfg["effects"]) or cfg["sharpen"] != "none" or cfg["aa"] != "none"


def to_post(cfg: Dict[str, Any]) -> str:
    """The engine's kfg_post string ("" = off). Effects in the engine's fixed order are fine in
    any order here: kfg_post_parse only sets bits."""
    cfg = normalize(cfg)
    parts = list(cfg["effects"])
    if cfg["sharpen"] == "cas":
        parts.append(f"cas={cfg['sharpness']:g}")
    elif cfg["sharpen"] == "dls":
        parts.append(f"dls={cfg['sharpness']:g}:{cfg['denoise']:g}")
    if cfg["aa"] != "none":
        parts.append(cfg["aa"])
    return ",".join(parts)


def summary(cfg: Dict[str, Any]) -> str:
    cfg = normalize(cfg)
    names = dict((k, n) for k, n, _ in EFFECTS)
    parts = [names[e] for e in cfg["effects"]]
    if cfg["sharpen"] != "none":
        parts.append(f"{cfg['sharpen'].upper()} {round(cfg['sharpness'] * 100)}%")
    if cfg["aa"] != "none":
        parts.append(cfg["aa"].upper())
    return " · ".join(parts) if parts else "Off"


def from_legacy(profile: Dict[str, Any]) -> Dict[str, Any]:
    """GFG 2.x vkBasalt settings (profile-wrapper-settings.json) -> 3.0 filters."""
    if not isinstance(profile, dict) or profile.get("external_vulkan_layer") != "vkbasalt":
        return dict(OFF)
    shader = str(profile.get("vkbasalt_shader") or "none")
    effects = [e for e in shader.split(":") if e and e != "none"]
    return normalize({"effects": effects, "sharpen": profile.get("vkbasalt_sharpening"),
                      "sharpness": profile.get("vkbasalt_sharpness", DEFAULT_SHARPNESS),
                      "denoise": profile.get("vkbasalt_dls_denoise", DEFAULT_DENOISE),
                      "aa": profile.get("vkbasalt_antialiasing")})


def catalog() -> Dict[str, Any]:
    return {"effects": [{"key": k, "name": n, "group": g} for k, n, g in EFFECTS],
            "presets": [{"id": p, "name": n, "filters": preset(p)} for p, n, _ in PRESETS],
            "sharpen": list(SHARPEN), "aa": list(AA)}
