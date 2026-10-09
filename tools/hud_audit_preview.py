#!/usr/bin/env python3
"""Preview actual HUD pixels for charge, savings, mode and unknown-data cases."""
import base64
import io
import sys
from pathlib import Path
from PIL import Image, ImageDraw
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from py_modules.gfg_plugin import hud_rings

base = {"fps": 90, "real": 30, "target": 90, "tdp": 15, "limit": 15,
        "maximum_tdp": 20, "energy_tdp": 15, "battery_pct": 72, "battery_min": 125,
        "frame_os": {"active": True, "level": "calm", "response": 47, "frames": 0,
                     "measured": {"response": True, "frames": False}}}
cases = [(f"Charge {pct}% / savings 25%", {**base, "battery_pct": pct}, "detailed")
         for pct in (100, 72, 50, 25, 5)]
cases += [("Frame OS disabled / charging / savings 25%", {**base, "frame_os": None, "battery_min": None}, "detailed"),
          ("Unknown charge and maximum", {**base, "battery_pct": None, "maximum_tdp": None}, "standard"),
          ("Zero readings", {**base, "fps": 0, "real": 0, "tdp": 0, "energy_tdp": 0}, "minimal")]
canvas = Image.new("RGB", (520, len(cases)*105), (28, 32, 42))
draw = ImageDraw.Draw(canvas)
for row, (label, data, preset) in enumerate(cases):
    draw.text((12, row*105+5), label, fill=(240,240,240))
    w,h,px = hud_rings.render(data,preset)
    rgba = Image.frombytes("RGBA",(w,h),px,"raw","BGRA")
    canvas.paste(rgba,(12,row*105+23),rgba)
    assert w+24<=520
canvas.save("hud-audit-preview.png")
buf=io.BytesIO();canvas.save(buf,format="PNG")
print("HUD_PREVIEW_BASE64="+base64.b64encode(buf.getvalue()).decode())
print("HUD preview: eight actual pixel cases, ENERGY text and charge arc independently exercised")
