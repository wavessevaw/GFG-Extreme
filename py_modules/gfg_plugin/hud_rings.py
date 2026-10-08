"""The ring HUD: a small bitmap of rings (FPS, TDP, battery, Frame OS benefit) for the game's corner.

Pure Python (the Deck's plugin Python has no imaging library): anti-aliased rings computed per
pixel, text from a pre-rendered Inter atlas (``hud_font_data``).  The result is composited on an
opaque panel and written as BGRA with a 32-byte header for the GFG HUD Vulkan layer
(engine/gfg-hud), which copies it into every presented frame.  Alpha 0 marks pixels outside the
rounded panel; every other pixel is opaque.  The caller refreshes at most once a second; geometry and glyph decoding are cached.
"""
from __future__ import annotations

import base64
import colorsys
import json
import math
import os
import struct
import zlib
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

MAGIC = 0x48474647          # "GFGH"
VERSION = 1
HEADER = struct.Struct("<8I")
CORNERS = {"top-left": 0, "top-right": 1, "bottom-left": 2, "bottom-right": 3}
DEFAULT_PATH = Path("/dev/shm/gfg-hud.raw")
DEFAULT_EXTENT = Path("/dev/shm/gfg-hud.extent")
SCALES = (1.0, 1.5, 2.0, 3.0)

PANEL = (14, 14, 17)
TRACK = (255, 255, 255, 0.16)
BRAND = (251, 13, 0)
WHITE = (245, 245, 247)
LABEL = (231, 231, 234)
GREY = (92, 92, 102)

_ATLAS: Optional[Dict[str, Any]] = None


def _atlas() -> Dict[str, Any]:
    global _ATLAS
    if _ATLAS is None:
        from .hud_font_data import DATA
        _ATLAS = json.loads(zlib.decompress(base64.b64decode("".join(DATA))))
    return _ATLAS


def scale_for(height: int) -> float:
    """Pick the atlas scale for a swapchain height (800 p = 1.0)."""
    want = max(1.0, height / 800.0)
    return min(SCALES, key=lambda s: abs(s - want))


def effect_color(value: float, full: float) -> Tuple[int, int, int]:
    """Red when worse; orange (little) -> yellow -> green (a lot)."""
    hue = 0.0 if value < 0 else 25.0 + 115.0 * min(1.0, abs(value) / full)
    r, g, b = colorsys.hls_to_rgb(hue / 360.0, 0.55, 0.85)
    return round(r * 255), round(g * 255), round(b * 255)


@lru_cache(maxsize=8)
def _panel(w: int, h: int, radius: float) -> bytes:
    """Bounded cache of immutable rounded backgrounds, copied for each update."""
    px = bytearray(w * h * 4)
    color = bytes((PANEL[2], PANEL[1], PANEL[0], 255))
    for y in range(h):
        for x in range(w):
            cx = min(max(x + 0.5, radius), w - radius)
            cy = min(max(y + 0.5, radius), h - radius)
            if (x + 0.5 - cx) ** 2 + (y + 0.5 - cy) ** 2 <= radius * radius:
                i = (y * w + x) * 4
                px[i:i + 4] = color
    return bytes(px)


@lru_cache(maxsize=32)
def _ring_geometry(size: float, width: float, cx: float, cy: float) -> tuple:
    """Only pixels touching the ring; cx/cy are subpixel offsets, not panel positions."""
    r, half = (size - width) / 2.0, width / 2.0
    points = []
    for y in range(math.floor(cy - size / 2) - 1, math.ceil(cy + size / 2) + 2):
        for x in range(math.floor(cx - size / 2) - 1, math.ceil(cx + size / 2) + 2):
            dx, dy = x + 0.5 - cx, y + 0.5 - cy
            band = min(1.0, max(0.0, half + 0.5 - abs(math.hypot(dx, dy) - r)))
            if band > 0:
                points.append((x, y, dx, dy, band, math.atan2(dx, -dy) % (2 * math.pi)))
    return tuple(points)


@lru_cache(maxsize=512)
def _glyph_alpha(encoded: str) -> bytes:
    return base64.b64decode(encoded)


class Canvas:
    def __init__(self, w: int, h: int, radius: float) -> None:
        self.w, self.h = w, h
        self.px = bytearray(_panel(w, h, radius))

    def blend(self, x: int, y: int, rgb: Tuple[int, int, int], a: float) -> None:
        if a <= 0 or not (0 <= x < self.w and 0 <= y < self.h):
            return
        i = (y * self.w + x) * 4
        if self.px[i + 3] == 0:
            return
        a = min(1.0, a)
        b, g, r = self.px[i], self.px[i + 1], self.px[i + 2]
        self.px[i] = round(b + (rgb[2] - b) * a)
        self.px[i + 1] = round(g + (rgb[1] - g) * a)
        self.px[i + 2] = round(r + (rgb[0] - r) * a)

    def ring(self, cx: float, cy: float, size: float, width: float, frac: float,
             rgb: Tuple[int, int, int], opacity: float = 1.0) -> None:
        r = (size - width) / 2.0
        half = width / 2.0
        frac = max(0.0, min(1.0, frac))
        end = frac * 2 * math.pi
        caps = [] if frac <= 0 else [(0.0, -r), (r * math.sin(end), -r * math.cos(end))]
        ox, oy = math.floor(cx), math.floor(cy)
        for x, y, dx, dy, band, angle in _ring_geometry(size, width, cx - ox, cy - oy):
            self.blend(x + ox, y + oy, TRACK[:3], band * TRACK[3])
            if frac <= 0:
                continue
            arc = band * min(1.0, max(0.0, (end - angle) * r + 0.5)) if frac < 1 else band
            for px, py in caps:
                arc = max(arc, min(1.0, max(0.0, half + 0.5 - math.hypot(dx - px, dy - py))))
            self.blend(x + ox, y + oy, rgb, arc * opacity)

    def text_width(self, text: str, style: str) -> float:
        font = _atlas()[style]
        widths = [font["glyphs"].get(ch, font["glyphs"][" "])["adv"] for ch in text]
        return sum(widths) + font["spacing"] * max(0, len(text) - 1)

    def text(self, cx: float, top: float, text: str, style: str, rgb: Tuple[int, int, int]) -> float:
        """Centered at cx; returns the line height."""
        font = _atlas()[style]
        x = cx - self.text_width(text, style) / 2.0
        for ch in text:
            g = font["glyphs"].get(ch, font["glyphs"][" "])
            alpha = _glyph_alpha(g["a"])
            gx = round(x + g["x0"])
            for row in range(g["h"]):
                for col in range(g["w"]):
                    a = alpha[row * g["w"] + col]
                    if a:
                        self.blend(gx + col, round(top) + row, rgb, a / 255.0)
            x += g["adv"] + font["spacing"]
        return font["ascent"] + font["descent"]

    def line(self, x: int, y0: int, y1: int, rgb: Tuple[int, int, int], a: float) -> None:
        for y in range(y0, y1):
            self.blend(x, y, rgb, a)

    def pill(self, x0: float, y0: float, x1: float, y1: float, rgb: Tuple[int, int, int], a: float) -> None:
        r = (y1 - y0) / 2.0
        for y in range(int(y0), int(y1) + 1):
            for x in range(int(x0), int(x1) + 1):
                cx = min(max(x + 0.5, x0 + r), x1 - r)
                d = math.hypot(x + 0.5 - cx, y + 0.5 - (y0 + r))
                self.blend(x, y, rgb, a * min(1.0, max(0.0, r + 0.5 - d)))


def _fmt_pct(value: float, sign_good: str) -> str:
    """Response shows a drop ("−47%"), frames a gain ("+50%"); worse flips the sign."""
    n = abs(round(value))
    if sign_good == "-":
        return ("−" if value >= 0 else "+") + f"{n}%"
    if sign_good == "+":
        return ("+" if value >= 0 else "−") + f"{n}%"
    return ("−" if value < 0 else "") + f"{n}%"


def items_for(data: Dict[str, Any], preset: str) -> List[Dict[str, Any]]:
    """What to draw, left to right."""
    items: List[Dict[str, Any]] = []
    fps, target = data.get("fps"), data.get("target") or 60
    real = data.get("real")
    items.append({"kind": "ring", "size": 52, "w": 4.5, "frac": (fps or 0) / target, "rgb": BRAND,
                  "text": str(round(fps)) if fps is not None else "—", "style": "fps",
                  "sub": f"{round(real)} REAL" if real is not None else None, "label": "OUT FPS"})
    tdp, limit = data.get("tdp"), data.get("limit") or 15
    items.append({"kind": "ring", "size": 46, "w": 4, "frac": (tdp or 0) / limit, "rgb": WHITE,
                  "text": f"{round(tdp)}W" if tdp is not None else "—", "style": "val", "label": "TDP CAP"})
    if preset == "detailed" and data.get("battery_min") is not None:
        mins = int(data["battery_min"])
        low = mins < 20
        items.append({"kind": "ring", "size": 46, "w": 4, "frac": (data.get("battery_pct") or 0) / 100.0,
                      "rgb": effect_color(5, 30) if low else WHITE,
                      "text": f"{mins // 60}h{mins % 60:02d}" if mins >= 60 else f"{mins}M", "style": "val",
                      "label": "BATTERY"})
    fos = data.get("frame_os")
    if preset != "minimal" and fos:
        items.append({"kind": "sep"})
        est, level = bool(fos.get("estimate")), fos.get("level")
        # The percentages have *different denominators*; do not label them as
        # input latency or battery energy savings. All are session aggregates.
        for key, full, sign, label, live in (("response", 50, "-", "AGE EST", level != "rest"),
                                             ("frames", 50, "+", "REAL GAIN", level == "boost"),
                                             ("energy", 30, "", "CAP CUT", level == "rest")):
            v = fos.get(key)
            items.append({"kind": "ring", "size": 40, "w": 3.5,
                          "frac": abs(v) / full if v is not None else 0,
                          "rgb": GREY if est or v is None else effect_color(v, full),
                          "opacity": 1.0 if (live or est) else 0.45,
                          "text": _fmt_pct(v, sign) if v is not None else "—", "style": "ben",
                          "label": label})
        # A visible status in Standard as well as Detailed. "BOOST" is earned:
        # a requested policy is not the same as an acknowledged real-cadence gain.
        if fos.get("mode") in ("observe", "shadow"):
            items.append({"kind": "tag", "text": fos["mode"].upper() + " EST", "rgb": GREY})
        elif fos.get("mode") == "act" and not fos.get("active"):
            items.append({"kind": "tag", "text": "ACT WAIT", "rgb": GREY})
        elif fos.get("active") and level in ("boost", "rest", "calm"):
            if level == "boost" and fos.get("verified_boost"):
                real = fos.get("actual_real")
                ratio = fos.get("actual_ratio")
                suffix = ""
                if isinstance(real, (int, float)) and isinstance(ratio, (int, float)) and ratio > 0:
                    multiplier = str(round(ratio)) if abs(ratio - round(ratio)) < 0.1 else f"{ratio:.1f}"
                    suffix = f" {round(real)}R x{multiplier}"
                label, colour = "BOOST" + suffix, (95, 240, 160)
            elif level == "boost":
                label, colour = "VERIFYING", GREY
            elif level == "rest":
                label, colour = "REST", (223, 230, 242)
            else:
                label, colour = "CALM", (223, 230, 242)
            items.append({"kind": "tag", "text": label, "rgb": colour})
    return items


def render(data: Dict[str, Any], preset: str = "standard", scale: float = 1.0) -> Tuple[int, int, bytes]:
    s = scale
    items = items_for(data, preset)
    pad_x, pad_y, gap = 8 * s, 6 * s, 6 * s
    col = 52 * s
    widths = []
    for it in items:
        if it["kind"] == "ring":
            widths.append(max(it["size"] * s, 0))
        elif it["kind"] == "sep":
            widths.append(5 * s)
        else:
            widths.append(len(it["text"]) * 6.2 * s + 12 * s)
    lab_h = 11 * s
    w = math.ceil(pad_x * 2 + sum(widths) + gap * (len(items) - 1))
    h = math.ceil(pad_y * 2 + col + 2 * s + lab_h)
    cv = Canvas(w, h, 12 * s)
    x = pad_x
    for it, iw in zip(items, widths):
        cx = x + iw / 2.0
        if it["kind"] == "ring":
            size = it["size"] * s
            cy = pad_y + col / 2.0
            cv.ring(cx, cy, size, it["w"] * s, it["frac"], it["rgb"], it.get("opacity", 1.0))
            style = f"{it['style']}@{s}"
            th = _atlas()[style]["ascent"]
            sub = it.get("sub")
            sub_style = f"sub@{s}"
            total = th + (_atlas()[sub_style]["ascent"] + 2 * s if sub else 0)
            top = cy - total / 2.0 - _atlas()[style]["descent"] * 0.15
            cv.text(cx, top, it["text"], style, WHITE)
            if sub:
                cv.text(cx, top + th + 1 * s, sub, sub_style, (220, 220, 226))
            cv.text(cx, pad_y + col + 2 * s, it["label"], f"lab@{s}", LABEL)
        elif it["kind"] == "sep":
            cv.line(round(cx), round(pad_y + 6 * s), round(pad_y + col - 6 * s), WHITE, 0.18)
        else:
            y0 = pad_y + col / 2.0 - 7 * s
            cv.pill(x, y0, x + iw, y0 + 14 * s, it["rgb"], 0.22)
            cv.text(cx, y0 + 2 * s, it["text"], f"lab@{s}", it["rgb"])
        x += iw + gap
    return w, h, bytes(cv.px)


def overlay_scale(extent_path: Path = DEFAULT_EXTENT) -> float:
    try:
        return scale_for(int(extent_path.read_text().split()[1]))
    except (OSError, ValueError, IndexError):
        return 1.0


def visual_key(data: Dict[str, Any], preset: str, position: str, scale: float) -> tuple:
    """Same visible items require neither rasterization nor a new Vulkan upload."""
    return preset, position, scale, json.dumps(items_for(data, preset), sort_keys=True)


def write_overlay(data: Optional[Dict[str, Any]], *, preset: str, position: str, seq: int,
                  path: Path = DEFAULT_PATH, extent_path: Path = DEFAULT_EXTENT,
                  scale: Optional[float] = None) -> bool:
    """Render and publish atomically; ``data`` None clears the HUD (a 0x0 overlay)."""
    if scale is None:
        scale = overlay_scale(extent_path)
    if data is None:
        w, h, pixels = 0, 0, b""
    else:
        w, h, pixels = render(data, preset, scale)
    header = HEADER.pack(MAGIC, VERSION, w, h, CORNERS.get(position, 0), round(12 * scale), seq & 0xFFFFFFFF, 0)
    tmp = path.with_name(f".{path.name}.{os.getpid()}")
    try:
        with open(tmp, "wb") as handle:
            handle.write(header)
            handle.write(pixels)
        os.replace(tmp, path)
        return True
    except OSError:
        try:
            tmp.unlink()
        except OSError:
            pass
        return False
