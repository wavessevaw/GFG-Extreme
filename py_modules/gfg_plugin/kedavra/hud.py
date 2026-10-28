# SPDX-License-Identifier: GPL-3.0-or-later
"""On-screen HUD: rings with the frame rate that reaches the screen.

GFG Extreme 3.0: vendored from GSF Kedavra; GFG red accent, wolf logo, and the GFG rings
(TDP, TEMP, GEN cost) next to the engine's, with three detail levels.

The plugin renders a small BGRA bitmap once a second and publishes it atomically; the
KEDAVRA Gamescope draws it as a layer of every composited frame (kfg_hud). The numbers come
from the engine's status file, so they count real KMS page flips, generated frames included,
not what the game submits.

Rings (the look follows GFG Extreme's ring HUD, in the KEDAVRA green: dark rounded panel with
the logo, thin track, coloured arc, number in the middle, label below):
  FPS   new frames on screen per second (real + generated; with generation off, the game's own
        frames). Not the KMS flip rate: Gamescope also flips for the Steam menu and overlays,
        which made the ring read 90 while the game ran at 25. Below: the game's own fps.
  x2/x3 the current multiplier; arc = share of generated frames; label AUTO in auto mode, CAP
        and the base cap with a fixed base frame rate (x2.3 for 40 at 90 Hz)
  PACE  share of vblanks that showed a new frame (not a repeat); green when above 99.5%

File: 8 x u32 header {magic 'KFGH', version 1, width, height, corner, margin, sequence, 0},
then width * height * 4 bytes BGRA; alpha 0 outside the panel. Width 0 hides the HUD.
"""
from __future__ import annotations

import base64
import json
import math
import os
import struct
import zlib
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

MAGIC = 0x4847464B  # "KFGH"
VERSION = 1
HEADER = struct.Struct("<8I")
CORNERS = {"top-left": 0, "top-right": 1, "bottom-left": 2, "bottom-right": 3, "centre": 4}  # centre: GSF 1.4.2
DEFAULT_PATH = Path("/dev/shm/kedavra-hud.raw")

PANEL = (6, 9, 7)
TRACK = (255, 255, 255)
TRACK_ALPHA = 0.14
RED = (255, 120, 40)    # a problem (amber-red, apart from the GFG accent)
ACCENT = (251, 13, 0)   # GFG Extreme red
GREEN = (82, 214, 74)
YELLOW = (227, 192, 74)
GREY = (111, 125, 117)
WHITE = (242, 246, 243)
LABEL = (207, 214, 209)

Rgb = Tuple[int, int, int]


@lru_cache(maxsize=1)
def _atlas() -> Dict[str, Any]:
    from .hud_font import DATA
    return json.loads(zlib.decompress(base64.b64decode("".join(DATA))))


@lru_cache(maxsize=4)
def _logo(scale: float) -> Optional[Tuple[int, bytes]]:
    try:
        from .hud_logo import LOGO
        px, data = LOGO[f"{scale:.2f}"]
        return px, zlib.decompress(base64.b64decode(data))
    except (ImportError, KeyError, ValueError, zlib.error):
        return None


@lru_cache(maxsize=1024)
def _coverage(encoded: str) -> bytes:
    return base64.b64decode(encoded)


HUD_SIZE = 0.88      # the HUD is 12 % smaller than the 3.0.0 one
SCALES = (0.88, 1.32, 1.76)
NUMBER_RISE = 4.0    # digit centre above the ring centre when a second line follows, HUD pixels


def scale_for(height: int) -> float:
    """Atlas scale for the output height (800 p = 0.88)."""
    base = min((1.0, 1.5, 2.0), key=lambda s: abs(s - max(1.0, height / 800.0)))
    return round(base * HUD_SIZE, 2)


def _advance(font: Dict[str, Any], g: Dict[str, Any]) -> int:
    return round(g["adv"] + font["spacing"])


@lru_cache(maxsize=32)
def _digit_top(style: str) -> float:
    """Top of the digits below the top of the line box."""
    return float(_atlas()[style]["glyphs"]["0"]["y0"])


@lru_cache(maxsize=32)
def _digit_mid(style: str) -> float:
    """Middle of the digits below the top of the line box."""
    g = _atlas()[style]["glyphs"]["0"]
    return g["y0"] + g["h"] / 2.0


class Canvas:
    """BGRA pixels on an opaque rounded panel; alpha 0 outside it."""

    def __init__(self, w: int, h: int, radius: float) -> None:
        self.w, self.h = w, h
        self.px = bytearray(_panel(w, h, radius))

    @classmethod
    def plain(cls, w: int, h: int) -> "Canvas":
        """A tile filled with the panel colour, opaque everywhere."""
        cv = cls.__new__(cls)
        cv.w, cv.h = w, h
        cv.px = bytearray(bytes((PANEL[2], PANEL[1], PANEL[0], 255)) * (w * h))
        return cv

    def paste(self, x0: int, y0: int, w: int, h: int, px: bytes,
              spans: Optional[List[Tuple[int, int]]] = None) -> None:
        """Copy a tile in where the panel is (outside it stays transparent): one slice per row,
        the panel being a rounded rectangle, one opaque span per row (precomputed per panel
        size when given: the scan was a third of the HUD's CPU)."""
        for row in range(h):
            y = y0 + row
            if not 0 <= y < self.h:
                continue
            a, b = spans[y] if spans is not None else self._span(y)
            lo, hi = max(x0, a), min(x0 + w, b)
            if lo < hi:
                self.px[(y * self.w + lo) * 4:(y * self.w + hi) * 4] = px[(row * w + lo - x0) * 4:(row * w + hi - x0) * 4]

    def _span(self, y: int) -> Tuple[int, int]:
        row = self.px[y * self.w * 4:(y + 1) * self.w * 4]
        alpha = row[3::4]
        a = next((i for i, v in enumerate(alpha) if v), self.w)
        b = self.w - next((i for i, v in enumerate(reversed(alpha)) if v), self.w)
        return a, max(a, b)

    def blend(self, x: int, y: int, rgb: Rgb, a: float) -> None:
        if a <= 0 or not (0 <= x < self.w and 0 <= y < self.h):
            return
        i = (y * self.w + x) * 4
        if self.px[i + 3] == 0:
            return
        a = min(1.0, a)
        for k, c in ((0, rgb[2]), (1, rgb[1]), (2, rgb[0])):
            self.px[i + k] = round(self.px[i + k] + (c - self.px[i + k]) * a)

    def ring(self, cx: float, cy: float, size: float, width: float, frac: float, rgb: Rgb) -> None:
        """Track plus an arc clockwise from 12 o'clock with round caps."""
        r = (size - width) / 2.0
        half = width / 2.0
        frac = max(0.0, min(1.0, frac))
        end = frac * 2 * math.pi
        caps = [(0.0, -r), (r * math.sin(end), -r * math.cos(end))] if frac > 0 else []
        for y in range(math.floor(cy - size / 2) - 1, math.ceil(cy + size / 2) + 2):
            for x in range(math.floor(cx - size / 2) - 1, math.ceil(cx + size / 2) + 2):
                dx, dy = x + 0.5 - cx, y + 0.5 - cy
                band = max(0.0, min(1.0, half + 0.5 - abs(math.hypot(dx, dy) - r)))
                if band <= 0:
                    continue
                self.blend(x, y, TRACK, band * TRACK_ALPHA)
                if frac <= 0:
                    continue
                if frac >= 1:
                    arc = band
                else:
                    angle = math.atan2(dx, -dy) % (2 * math.pi)
                    arc = band * max(0.0, min(1.0, (end - angle) * r + 0.5))
                    for px, py in caps:
                        arc = max(arc, max(0.0, min(1.0, half + 0.5 - math.hypot(dx - px, dy - py))))
                self.blend(x, y, rgb, arc)

    def image(self, x0: int, y0: int, size: int, rgba: bytes) -> None:
        for y in range(size):
            for x in range(size):
                i = (y * size + x) * 4
                a = rgba[i + 3]
                if a:
                    self.blend(x0 + x, y0 + y, (rgba[i], rgba[i + 1], rgba[i + 2]), a / 255.0)

    def text_width(self, text: str, style: str) -> float:
        font = _atlas()[style]
        space = font["glyphs"][" "]
        return float(sum(_advance(font, font["glyphs"].get(ch, space)) for ch in text[:-1])
                     + (font["glyphs"].get(text[-1], space)["adv"] if text else 0.0))

    def text(self, cx: float, top: float, text: str, style: str, rgb: Rgb) -> None:
        """Centred on cx; top is the top of the line box."""
        font = _atlas()[style]
        space = font["glyphs"][" "]
        # Whole-pixel pen steps: small letters keep even gaps instead of jittering by rounding.
        x = float(round(cx - self.text_width(text, style) / 2.0))
        for ch in text:
            g = font["glyphs"].get(ch, space)
            cov = _coverage(g["a"])
            gx, gy = round(x + g["x0"]), round(top + g["y0"])
            for row in range(g["h"]):
                for col in range(g["w"]):
                    a = cov[row * g["w"] + col]
                    if a:
                        self.blend(gx + col, gy + row, rgb, a / 255.0)
            x += _advance(font, g)


@lru_cache(maxsize=8)
def _panel(w: int, h: int, radius: float) -> bytes:
    px = bytearray(w * h * 4)
    color = bytes((PANEL[2], PANEL[1], PANEL[0], 255))
    for y in range(h):
        for x in range(w):
            cx = min(max(x + 0.5, radius), w - radius)
            cy = min(max(y + 0.5, radius), h - radius)
            if (x + 0.5 - cx) ** 2 + (y + 0.5 - cy) ** 2 <= radius * radius:
                px[(y * w + x) * 4:(y * w + x) * 4 + 4] = color
    return bytes(px)


def _num(v: Any) -> Optional[float]:
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0:
        return None
    return float(v)


class Rates:
    """Per-second rates from consecutive engine status snapshots (cumulative counters)."""

    KEYS = ("flips", "sources", "real", "gen", "repeat")
    OPTIONAL = ("unsupported", "degrade")

    def __init__(self) -> None:
        self.prev: Optional[Dict[str, Any]] = None

    def update(self, st: Dict[str, Any]) -> Optional[Dict[str, float]]:
        t = _num(st.get("time_ns"))
        if t is None:
            return None
        prev, self.prev = self.prev, st
        if prev is None or _num(prev.get("time_ns")) is None:
            return None
        dt = (t - prev["time_ns"]) / 1e9
        if not 0.2 <= dt <= 5.0:
            return None
        out = {}
        for k in self.KEYS:
            a, b = _num(prev.get(k)), _num(st.get(k))
            if a is None or b is None or b < a:
                return None
            out[k] = (b - a) / dt
        for k in self.OPTIONAL:
            a, b = _num(prev.get(k)), _num(st.get(k))
            out[k] = (b - a) / dt if a is not None and b is not None and b >= a else 0.0
        return out


def mult_text(v: float) -> str:
    """x2.25, x3.75 exactly (quarter steps); x2.6 for 35 at 90 Hz."""
    if abs(v * 4 - round(v * 4)) < 0.01:
        return "x" + f"{round(v * 4) / 4:.2f}".rstrip("0").rstrip(".")
    return f"x{v:.1f}"


def _rate_color(v: float, target: float) -> Rgb:
    return GREEN if v >= 0.97 * target else (YELLOW if v >= 0.85 * target else RED)


def live_for(st: Dict[str, Any], rates: Optional[Dict[str, float]]) -> Dict[str, Any]:
    """What the HUD and the panel show: fps on screen, the game's fps, pace, generated share."""
    active = st.get("state") == "active"
    if not rates or st.get("steam_ui") is True:
        # No rates yet, or Steam's own UI is on screen: its repaints are not game frames.
        return {"fps": None, "real": None, "pace": None, "gen_share": None, "unsupported": 0.0}
    real = rates["sources"]
    shown = rates["real"] + rates["gen"] + rates["repeat"]
    # New frames per second, never more than the flips that carried them.
    fps = min(rates["flips"], rates["real"] + rates["gen"]) if active else min(rates["flips"], real)
    return {"fps": fps, "real": real,
            "pace": 1.0 - rates["repeat"] / shown if active and shown > 0 else None,
            "gen_share": rates["gen"] / shown if active and shown > 0 else 0.0,
            # Paints per second whose game frame generation could not take (format, HDR).
            "unsupported": rates.get("unsupported", 0.0)}


def items_for(st: Dict[str, Any], rates: Optional[Dict[str, float]]) -> List[Dict[str, Any]]:
    refresh = 1e9 / st["refresh_ns"] if _num(st.get("refresh_ns")) else 90.0
    active = st.get("state") == "active"
    lv = live_for(st, rates)
    real, fps = lv["real"], lv["fps"]
    shown = (rates["real"] + rates["gen"] + rates["repeat"]) if rates else 0.0
    base = st.get("base_fps") if isinstance(st.get("base_fps"), int) else 0
    items = [{
        "size": 54, "w": 4, "frac": (fps or 0) / refresh,
        "rgb": _rate_color(fps or 0, refresh) if active else GREEN,
        "text": str(round(fps)) if fps is not None else "—", "style": "fps",
        "sub": f"{round(real)} REAL" if real is not None else None, "label": "FPS"}]
    mult = st.get("multiplier") if isinstance(st.get("multiplier"), int) else 1
    gen_share = rates["gen"] / shown if rates and shown > 0 else 0.0
    # Auto picks its cap too (30, 35, 40 or 45 at 90 Hz): x2.6 at 35, not the scheduler's 3.
    cap = st.get("cap_fps") if isinstance(st.get("cap_fps"), int) else 0
    eff = base or (cap if st.get("auto") else 0)
    if active and eff and round(refresh) % eff:
        text = mult_text(round(refresh) / eff)
    else:
        text = f"x{mult}" if active and mult > 1 else "OFF"
    label = f"CAP {base}" if base else ("AUTO" if st.get("auto") else "GEN")
    items.append({
        "size": 48, "w": 3.5, "frac": gen_share if active else 0.0, "rgb": ACCENT if active else GREY,
        "text": text, "style": "val", "label": label})
    if active and rates and shown > 0:
        new = 1.0 - rates["repeat"] / shown
        rgb = GREEN if new >= 0.995 else (YELLOW if new >= 0.97 else RED)
        items.append({"size": 48, "w": 3.5, "frac": new, "rgb": rgb,
                      "text": f"{min(99.9, 100 * new):.1f}" if new < 0.9995 else "100", "style": "val",
                      "label": "PACE"})
    return items


DETAIL_RINGS = {"minimal": ("FPS", "MULT"),
                "standard": ("FPS", "TDP", "MULT", "TEMP", "BATTERY", "PACE")}


def battery_ring(battery: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """The number is the time left (H:MM) on battery, AC on external power; the ring is the charge."""
    pct = _num(battery.get("percent"))
    if pct is None:
        return None
    if battery.get("external_power"):
        text = "AC"
    else:
        hours = _num(battery.get("hours_left"))
        text = f"{int(hours)}:{int(round((hours % 1) * 60)) % 60:02d}" if hours is not None and hours < 100 else "—"
    rgb = GREEN if pct >= 50 else (YELLOW if pct >= 20 else RED)
    return {"size": 48, "w": 3.5, "frac": min(1.0, pct / 100.0), "rgb": rgb, "text": text, "style": "val",
            "label": "BATTERY H"}


def gfg_items(st: Dict[str, Any], rates: Optional[Dict[str, float]], extra: Dict[str, Any],
              detail: str = "standard") -> List[Dict[str, Any]]:
    """The approved 3.0 HUD: FPS, TDP, multiplier, temperature, battery, pacing. One number per
    ring, the unit in the label, no glow."""
    base = items_for(st, rates)
    # The real frame rate goes under the ring, so the number stays centred like the others.
    real = base[0].get("sub")
    named = {"FPS": {**base[0], "sub": None, "label": f"FPS · {real}" if real else "FPS"}, "MULT": base[1]}
    if len(base) > 2:
        named["PACE"] = {**base[2], "label": "PACE %"}
    tdp = _num(extra.get("tdp_w"))
    if tdp is not None:
        ceiling = _num(extra.get("ceiling_w")) or 15.0
        named["TDP"] = {"size": 48, "w": 3.5, "frac": tdp / max(ceiling, tdp), "rgb": ACCENT,
                        "text": f"{tdp:.1f}" if tdp < 10 else f"{tdp:.0f}", "style": "val", "label": "TDP W"}
    temp = _num(extra.get("temp_c"))
    if temp is not None:
        named["TEMP"] = {"size": 48, "w": 3.5, "frac": min(1.0, temp / 100.0),
                         "rgb": GREEN if temp < 75 else (YELLOW if temp < 85 else RED),
                         "text": f"{temp:.0f}", "style": "val", "label": "TEMP C"}
    bat = battery_ring(extra.get("battery") or {})
    if bat is not None:
        named["BATTERY"] = bat
    order = DETAIL_RINGS.get(detail, DETAIL_RINGS["standard"])
    return [named[k] for k in order if k in named]


def _item_tile(it: Dict[str, Any], s: float, tw: int, th: int, ox: float, oy: float, label_top: float) -> bytes:
    """One ring with its number and label, drawn on a plain panel-coloured tile."""
    cv = Canvas.__new__(Canvas)
    cv.w, cv.h = tw, th
    atlas = _atlas()
    iw = it["size"] * s
    cx, cy = ox + iw / 2.0, oy
    # The ring is most of the drawing and only shows a few hundred arcs: drawn once, the number
    # and the label go on a copy.
    cv.px = bytearray(_ring_tile(tw, th, cx, cy, it["size"] * s, it["w"] * s, it["frac"], tuple(it["rgb"])))
    style = f"{it['style']}@{s}"
    inner = (it["size"] - 2 * it["w"] - 9) * s
    if it["style"] == "val" and cv.text_width(it["text"], style) > inner:
        style = f"vsm@{s}"   # x2.25, 99.7, 0:30: the smaller cut, still inside the ring
    sub_style = f"sub@{s}"
    # The digits' own middle on the ring's centre, whatever the font or the number of
    # characters; a ring with a second line lifts its number to make room for it.
    sub = it.get("sub")
    top = cy - (NUMBER_RISE * s if sub else 0.0) - _digit_mid(style)
    cv.text(cx, top, it["text"], style, WHITE)
    if sub:
        cv.text(cx, top + atlas[style]["ascent"] + 2 * s - _digit_top(sub_style), sub, sub_style, LABEL)
    cv.text(cx, label_top, it["label"], f"lab@{s}", LABEL)
    return bytes(cv.px)


RING_STEPS = 256   # arc ends a fraction of a pixel apart look the same: 1/256 of a turn


def ring_frac(frac: Any) -> float:
    """The ring's fill on the steps it is drawn at (0 for a missing value)."""
    if not isinstance(frac, (int, float)) or isinstance(frac, bool) or not math.isfinite(frac):
        return 0.0
    return round(max(0.0, min(1.0, float(frac))) * RING_STEPS) / RING_STEPS


@lru_cache(maxsize=768)
def _ring_tile(tw: int, th: int, cx: float, cy: float, size: float, width: float, frac: float, rgb: Rgb) -> bytes:
    cv = Canvas.plain(tw, th)
    cv.ring(cx, cy, size, width, frac, rgb)
    return bytes(cv.px)


@lru_cache(maxsize=8)
def _spans(w: int, h: int, s: float) -> List[Tuple[int, int]]:
    """The panel's opaque span on each row, for one HUD size."""
    cv = Canvas.plain(w, h)
    cv.px = bytearray(_base(w, h, s))
    return [cv._span(y) for y in range(h)]


@lru_cache(maxsize=8)
def _base(w: int, h: int, s: float) -> bytes:
    """The panel with the logo: the same for every frame of one HUD size."""
    cv = Canvas(w, h, 12 * s)
    logo = _logo(s)
    if logo:
        pad_x, pad_y, col = 8 * s, 6 * s, 54 * s
        cv.image(round(pad_x), round(pad_y + (col - logo[0]) / 2), logo[0], logo[1])
    return bytes(cv.px)


_TILES: Dict[str, bytes] = {}


def render(st: Dict[str, Any], rates: Optional[Dict[str, float]], scale: float = SCALES[0],
           items: Optional[List[Dict[str, Any]]] = None) -> Tuple[int, int, bytes]:
    s = scale
    items = items if items is not None else items_for(st, rates)
    pad_x, pad_y, gap, col, lab_h = 8 * s, 6 * s, 7 * s, 54 * s, 11 * s
    widths = [it["size"] * s for it in items]
    logo = _logo(s)
    lw = logo[0] + gap if logo else 0
    w = math.ceil(2 * pad_x + lw + sum(widths) + gap * (len(items) - 1))
    h = math.ceil(2 * pad_y + col + 2 * s + lab_h)
    cv = Canvas.plain(w, h)
    cv.px = bytearray(_base(w, h, s))
    x = pad_x + lw
    for it, iw in zip(items, widths):
        # Ring and number are drawn once per value on a tile and copied in (the HUD changes
        # every second, but each ring only shows a few dozen values): the pixels are the same
        # as drawing them here, at a fraction of the CPU.
        x0, y0 = math.floor(x) - 2, math.floor(pad_y) - 2
        x1, y1 = min(w, math.ceil(x + iw) + 3), h
        tw, th = x1 - x0, y1 - y0
        it = {**it, "frac": ring_frac(it.get("frac"))}
        key = json.dumps([it.get(k) for k in ("size", "w", "frac", "rgb", "style", "text", "sub", "label")]
                         + [s, tw, th, x - x0, pad_y + col / 2.0 - y0], default=str)
        tile = _TILES.get(key)
        if tile is None:
            if len(_TILES) > 512:
                _TILES.clear()
            tile = _TILES[key] = _item_tile(it, s, tw, th, x - x0, pad_y + col / 2.0 - y0, pad_y + col + 2 * s - y0)
        cv.paste(x0, y0, tw, th, tile, _spans(w, h, s))
        x += iw + gap
    return w, h, bytes(cv.px)


def _fmt(v: Any, digits: int = 0) -> str:
    n = _num(v)
    return "—" if n is None else (f"{n:.{digits}f}" if digits else str(round(n)))


def render_message(panel: str, view: Dict[str, Any], scale: float = SCALES[0]) -> Tuple[int, int, bytes]:
    """The benchmark's centre panel (GFG 3.3.0): measuring with the seconds left and the live
    medians, then done or cancelled. The HUD atlas has capitals, digits and a few signs only."""
    s = scale
    w, h = math.ceil(380 * s), math.ceil(196 * s)
    cv = Canvas(w, h, 14 * s)
    cx = w / 2.0
    cv.text(cx, 12 * s, "GFG BENCHMARK", f"lab@{s}", ACCENT)
    if panel == "measuring":
        cv.text(cx, 28 * s, "DO NOT TOUCH ANYTHING", f"fps@{s}", WHITE)
        cv.text(cx, 56 * s, "MEASURING AT 15 W · GENERATION OFF", f"sub@{s}", LABEL)
        left = int(view.get("seconds_left") or 0)
        cy = 104 * s
        cv.ring(cx, cy, 58 * s, 6 * s, left / 20.0, ACCENT)
        cv.text(cx, cy - _digit_mid(f"fps@{s}"), str(left), f"fps@{s}", WHITE)
        live = view.get("live") or {}
        cells = [(_fmt(live.get("real")), "FPS"), (_fmt(live.get("gpu")) + "%", "GPU"), (_fmt(live.get("cpu")) + "%", "CPU"),
                 (_fmt(live.get("draw_w"), 1), "W"), (_fmt(live.get("temp_c")), "C")]
        step = (w - 40 * s) / len(cells)
        for i, (v, lab) in enumerate(cells):
            x = 20 * s + step * (i + 0.5)
            cv.text(x, 142 * s, v, f"val@{s}", WHITE)
            cv.text(x, 164 * s, lab, f"lab@{s}", LABEL)
    elif panel == "done":
        res = view.get("result") or {}
        cv.text(cx, 30 * s, "BENCHMARK DONE", f"fps@{s}", WHITE)
        line = f"BASE {res.get('point', '—')} · {res.get('multiplier', '')}"
        if res.get("watts"):
            line += f" · {res['watts']} W"
        cv.text(cx, 78 * s, line, f"val@{s}", ACCENT)
        cv.text(cx, 122 * s, "OPEN QUICK ACCESS TO ACCEPT", f"val@{s}", WHITE)
        cv.text(cx, 150 * s, "OR KEEP AUTOPILOT SEARCHING", f"sub@{s}", LABEL)
    else:
        cv.text(cx, 44 * s, "BENCHMARK CANCELLED", f"fps@{s}", WHITE)
        cv.text(cx, 96 * s, str(view.get("reason") or "").upper(), f"sub@{s}", LABEL)
        cv.text(cx, 130 * s, "START IT AGAIN FROM DASH", f"sub@{s}", LABEL)
    return w, h, bytes(cv.px)


def publish(path: Path, w: int, h: int, pixels: bytes, *, corner: str = "top-left",
            margin: int = 12, seq: int = 0) -> bool:
    """Atomic write; readable by the Gamescope user. w = 0 hides the HUD."""
    header = HEADER.pack(MAGIC, VERSION, w, h, CORNERS.get(corner, 0), margin, seq & 0xFFFFFFFF, 0)
    tmp = path.with_name(f".{path.name}.{os.getpid()}")
    try:
        with open(tmp, "wb") as f:
            f.write(header)
            f.write(pixels)
        os.chmod(tmp, 0o644)
        os.replace(tmp, path)
        return True
    except OSError:
        try:
            tmp.unlink()
        except OSError:
            pass
        return False


class Hud:
    """Called once a second by the plugin with the engine status (or None)."""

    def __init__(self, path: Path = DEFAULT_PATH) -> None:
        self.path = path
        self.rates = Rates()
        self.seq = 0
        self.last_key: Optional[str] = None
        self.shown = False
        self.live: Dict[str, Any] = live_for({}, None)

    def message(self, status: Optional[Dict[str, Any]], panel: str, view: Dict[str, Any]) -> bool:
        """A centre panel in place of the rings (needs GSF 1.4.2's centred HUD)."""
        scale = scale_for(int((status or {}).get("height") or 800))
        key = json.dumps(["msg", scale, panel, view.get("seconds_left"), view.get("live"), view.get("reason"),
                          (view.get("result") or {}).get("point")], sort_keys=True, default=str)
        self.seq += 1
        if key == self.last_key:
            try:
                os.utime(self.path)
                return True
            except OSError:
                pass
        w, h, px = render_message(panel, view, scale)
        self.last_key = key
        self.shown = True
        return publish(self.path, w, h, px, corner="centre", margin=0, seq=self.seq)

    def tick(self, enabled: bool, status: Optional[Dict[str, Any]], extra: Optional[Dict[str, Any]] = None,
             corner: str = "top-left", detail: str = "standard") -> bool:
        fresh = bool(status) and status.get("engine") == "running"
        rates = self.rates.update(status) if fresh else None
        if not fresh:
            self.rates.prev = None
        self.live = live_for(status or {}, rates)
        if not enabled or not fresh:
            if self.shown or self.last_key is None:
                self.shown = False
                self.last_key = ""
                return publish(self.path, 0, 0, b"", seq=self.seq)
            return True
        scale = scale_for(int(status.get("height") or 800))
        items = items_for(status, rates) if extra is None else gfg_items(status, rates, extra, detail)
        key = json.dumps([scale, corner, items], sort_keys=True, default=str)
        self.seq += 1
        if key == self.last_key:
            # Same picture: refresh the file time only, so Gamescope keeps showing it.
            try:
                os.utime(self.path)
                return True
            except OSError:
                pass
        w, h, px = render(status, rates, scale, items)
        self.last_key = key
        self.shown = True
        return publish(self.path, w, h, px, corner=corner, margin=round(12 * scale), seq=self.seq)
