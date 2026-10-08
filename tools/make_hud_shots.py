#!/usr/bin/env python3
"""Render README pictures of the ring HUD with the plugin's own renderer (developer tool; needs Pillow).

The rings are exactly the bitmap the GFG HUD layer copies into the game; the scene behind them
is an illustrative gradient. Usage: tools/make_hud_shots.py
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from py_modules.gfg_plugin import hud_rings  # noqa: E402

W, H = 1280, 800
SHOTS = {
    # Frame OS Act boosting in a fight: 45 real frames at 90 Hz.
    "standard": ({"fps": 90, "real": 45, "target": 90, "tdp": 15, "limit": 15,
                  "frame_os": {"estimate": False, "level": "boost", "response": 47, "frames": 50, "energy": 9}},
                 "top-left"),
    "minimal": ({"fps": 88, "real": 30, "target": 90, "tdp": 9, "limit": 15}, "top-left"),
    # A pause: Frame OS rests and saves energy.
    "detailed": ({"fps": 90, "real": 30, "target": 90, "tdp": 11, "limit": 15, "battery_min": 125,
                  "battery_pct": 72,
                  "frame_os": {"estimate": False, "level": "rest", "response": 45, "frames": 3, "energy": 14}},
                 "top-right"),
}


def scene() -> Image.Image:
    glow = ImageOps.colorize(Image.radial_gradient("L").resize((W * 2, H * 2)), "#2a3a52", "#10141c")
    img = glow.crop((W // 2 - 140, H // 2 - 240, W // 2 - 140 + W, H // 2 - 240 + H)).convert("RGB")
    draw = ImageDraw.Draw(img)
    for y in range(H - 260, H):
        t = (y - (H - 260)) / 260
        c = tuple(round(a + (b - a) * t) for a, b in zip((26, 31, 39), (11, 13, 17)))
        draw.line([(0, y), (W, y)], fill=c)
    draw.text((W - 230, H - 26), "illustrative scene · real HUD bitmap", fill=(85, 85, 102))
    return img


def main() -> None:
    for name, (data, position) in SHOTS.items():
        w, h, px = hud_rings.render(data, name, 1.0)
        bgra = Image.frombytes("RGBA", (w, h), px)
        b, g, r, a = bgra.split()
        hud = Image.merge("RGBA", (r, g, b, a))
        img = scene()
        x = 12 if position.endswith("left") else W - 12 - w
        img.paste(hud, (x, 12), hud)
        out = ROOT / "docs" / "img" / f"hud-rings-{name}.png"
        img.save(out, optimize=True)
        print("wrote", out)


if __name__ == "__main__":
    main()
