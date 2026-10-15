#!/usr/bin/env python3
"""Build a fake Steam install tree for GFG Shell tests and screenshots.

Every name and app id here is fictional. Layout mirrors the files GFG Shell reads:
libraryfolders.vdf (two libraries), appmanifest_*.acf (installed, not installed, a
Proton tool that must be hidden), loginusers.vdf, localconfig.vdf, binary
shortcuts.vdf (one appid with the sign bit set), Steam favorites JSON, and
artwork in both the legacy flat and the per-app librarycache layouts.

usage: make_fake_steam.py <out_dir> [--art] [--now <unix>]
"""
import argparse
import json
import os
import struct
import time

STEAMID = 76561198000000042           # -> account id 39734314
ACCOUNT = STEAMID - 76561197960265728

GAMES = [  # appid, name, library(0/1), state_flags, last_played_days_ago, playtime_min, size
    (4100010, "Neon Drift", 0, 4, 0, 1260, 8_400_000_000),
    (4100020, "Пепел Севера", 1, 4, 1, 5400, 41_000_000_000),
    (4100030, "Orbital Foundry", 0, 4, 6, 300, 2_100_000_000),
    (4100040, "Hollow Lantern", 1, 6, 20, 75, 12_000_000_000),
    (4100050, "Sky Courier", 0, 4, None, 0, 900_000_000),
    (4100060, "Glass Cathedral", 0, 2, None, 0, 0),           # not fully installed
    (4100070, "Tidebreaker", 1, 4, 45, 2200, 25_000_000_000),
    (4100080, "Quiet Engine", 0, 4, None, 0, 4_000_000_000),
    (1493710, "Proton Experimental", 0, 4, None, 0, 1_000_000_000),   # tool, hidden
]
SHORTCUTS = [  # signed int32 appid as Steam stores it
    (-1820446516, "Retro Arcade Hub", "/home/deck/Emu/arcade.sh", 3),
    (2081234567, "Indie Sketchbook", "/home/deck/Games/sketch/run.sh", None),
    (-1000000001, "GFG Shell", "/home/deck/.local/share/gfg-shell/gfg-shell.sh", None),  # must be hidden
]
PALETTE = [(227, 38, 47), (40, 90, 200), (30, 160, 120), (200, 140, 40), (120, 60, 180), (60, 60, 70), (20, 130, 170), (170, 60, 90)]


def acf(appid, name, flags, size, installdir, last_played=0, to_download=0, downloaded=0):
    return ('"AppState"\n{\n\t"appid"\t\t"%d"\n\t"universe"\t\t"1"\n\t"name"\t\t"%s"\n'
            '\t"StateFlags"\t\t"%d"\n\t"installdir"\t\t"%s"\n\t"LastPlayed"\t\t"%d"\n\t"SizeOnDisk"\t\t"%d"\n'
            '\t"BytesToDownload"\t\t"%d"\n\t"BytesDownloaded"\t\t"%d"\n'
            '\t"UserConfig"\n\t{\n\t\t"language"\t\t"russian"\n\t}\n}\n') % (
                appid, name, flags, installdir, last_played, size, to_download, downloaded)


def bin_str(k, v):
    return b"\x01" + k.encode() + b"\x00" + v.encode() + b"\x00"


def bin_int(k, v):
    return b"\x02" + k.encode() + b"\x00" + struct.pack("<i", v)


def shortcuts_vdf(now):
    out = b"\x00shortcuts\x00"
    for i, (appid, name, exe, days) in enumerate(SHORTCUTS):
        out += b"\x00" + str(i).encode() + b"\x00"
        out += bin_int("appid", appid) + bin_str("AppName", name) + bin_str("Exe", '"%s"' % exe)
        out += bin_str("StartDir", os.path.dirname(exe)) + bin_str("icon", "") + bin_str("LaunchOptions", "")
        out += bin_int("IsHidden", 0) + bin_int("LastPlayTime", now - days * 86400 if days is not None else 0)
        out += b"\x00tags\x00\x08"   # empty tags map
        out += b"\x08"
    return out + b"\x08\x08"


def art(path, size, color, text, logo=True):
    """Stand-in game art that reads like real key art: a dark sky toward the
    game's colour, a glow, layered silhouettes, grain, and the title as a logo
    (left out on heroes, which Steam ships without one)."""
    import random
    from PIL import Image, ImageDraw, ImageFilter, ImageFont
    w, h = size
    rnd = random.Random(text)
    img = Image.new("RGB", size)
    d = ImageDraw.Draw(img)
    dark = (8, 8, 12)
    for y in range(h):
        t = y / max(1, h - 1)
        k = (1 - t) ** 1.6
        d.line([(0, y), (w, y)], fill=tuple(int(dark[i] + (color[i] * 0.85 - dark[i]) * k) for i in range(3)))
    glow = Image.new("L", size, 0)
    gd = ImageDraw.Draw(glow)
    cx, cy, r = rnd.uniform(0.3, 0.8) * w, rnd.uniform(0.2, 0.45) * h, max(w, h) * 0.22
    gd.ellipse([cx - r, cy - r, cx + r, cy + r], fill=200)
    glow = glow.filter(ImageFilter.GaussianBlur(max(w, h) * 0.12))
    img = Image.composite(Image.new("RGB", size, tuple(min(255, c + 90) for c in color)), img, glow)
    d = ImageDraw.Draw(img)
    for layer in range(3):
        base = h * (0.55 + 0.13 * layer)
        shade = tuple(int(c * (0.35 - 0.11 * layer)) for c in color)
        pts, x = [(0, h)], 0
        while x <= w:
            pts.append((x, base - rnd.uniform(0, h * (0.28 - 0.06 * layer))))
            x += rnd.uniform(w * 0.03, w * 0.09)
        pts += [(w, h)]
        d.polygon(pts, fill=shade)
    noise = Image.effect_noise(size, 18).convert("RGB")
    img = Image.blend(img, noise, 0.05)
    if logo:
        # a capsule logo: one word per line on portrait art, sized to fit 84 % of the width
        lines = text.upper().split() if h > w else [text.upper()]
        path_ttf = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        size_px = min(h // 4, w // 3) if h > w else h // 4
        while True:
            try:
                font = ImageFont.truetype(path_ttf, size_px)
            except OSError:
                font = ImageFont.load_default()
                break
            if max(d.textlength(t, font=font) for t in lines) <= w * 0.84 or size_px <= 12:
                break
            size_px -= 2
        lh = int(font.size * 1.05)
        y0 = h * 0.5 - lh * len(lines) / 2 if h > w else h * 0.36
        shadow = Image.new("L", size, 0)
        sd = ImageDraw.Draw(shadow)
        for i, t in enumerate(lines):
            sd.text(((w - d.textlength(t, font=font)) / 2, y0 + i * lh), t, fill=255, font=font)
        shadow = shadow.filter(ImageFilter.GaussianBlur(6))
        img = Image.composite(Image.new("RGB", size, (0, 0, 0)), img, shadow)
        dd = ImageDraw.Draw(img)
        for i, t in enumerate(lines):
            dd.text(((w - d.textlength(t, font=font)) / 2, y0 + i * lh), t, fill=(250, 250, 250), font=font)
    if path.endswith(".png"):
        img.save(path)
    else:
        img.save(path, quality=90)


def logo_art(path, text):
    """Transparent title logo, as Steam's logo.png."""
    from PIL import Image, ImageDraw, ImageFont
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 120)
    except OSError:
        font = ImageFont.load_default()
    probe = ImageDraw.Draw(Image.new("L", (1, 1)))
    tw = int(probe.textlength(text.upper(), font=font))
    img = Image.new("RGBA", (tw + 40, 170), (0, 0, 0, 0))
    ImageDraw.Draw(img).text((20, 15), text.upper(), fill=(255, 255, 255, 255), font=font)
    img.crop(img.getbbox()).save(path)   # Steam's logos are cut to the artwork


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--art", action="store_true")
    ap.add_argument("--now", type=int, default=int(time.time()))
    a = ap.parse_args()
    root, sd = os.path.join(a.out, "Steam"), os.path.join(a.out, "sdcard")
    for p in (root + "/steamapps/common", sd + "/steamapps/common", root + "/config",
              root + "/userdata/%d/config/grid" % ACCOUNT, root + "/userdata/%d/config/cloudstorage" % ACCOUNT,
              root + "/appcache/librarycache"):
        os.makedirs(p, exist_ok=True)
    libs = [root, sd]
    with open(root + "/steamapps/libraryfolders.vdf", "w") as f:
        f.write('"libraryfolders"\n{\n')
        for i, lib in enumerate(libs):
            apps = "".join('\t\t\t"%d"\t\t"%d"\n' % (g[0], g[6]) for g in GAMES if g[2] == i)
            f.write('\t"%d"\n\t{\n\t\t"path"\t\t"%s"\n\t\t"label"\t\t""\n\t\t"apps"\n\t\t{\n%s\t\t}\n\t}\n' % (i, lib, apps))
        f.write("}\n")
    apps_cfg = ""
    for appid, name, lib, flags, days, minutes, size in GAMES:
        with open(libs[lib] + "/steamapps/appmanifest_%d.acf" % appid, "w") as f:
            # Sky Courier: LastPlayed only in its manifest (localconfig has no entry), the
            # newest of all: the shell must still list it first. Hollow Lantern: an update
            # half downloaded.
            last = a.now - 600 if name == "Sky Courier" else 0
            todo, done = (12_400_000_000, 5_300_000_000) if name == "Hollow Lantern" else (0, 0)
            f.write(acf(appid, name, flags, size, name.replace(" ", ""), last, todo, done))
        if days is not None:
            apps_cfg += '\t\t\t\t\t"%d"\n\t\t\t\t\t{\n\t\t\t\t\t\t"LastPlayed"\t\t"%d"\n\t\t\t\t\t\t"Playtime"\t\t"%d"\n\t\t\t\t\t}\n' % (
                appid, a.now - days * 86400 - 3600, minutes)
    with open(libs[0] + "/steamapps/appmanifest_9999.acf", "w") as f:
        f.write('"AppState"\n{\n\t"appid" "9999"\n')        # truncated: must be skipped, not crash
    with open(root + "/config/loginusers.vdf", "w") as f:
        f.write('"users"\n{\n\t"76561198000000001"\n\t{\n\t\t"AccountName"\t\t"old"\n\t\t"MostRecent"\t\t"0"\n\t\t"Timestamp"\t\t"1600000000"\n\t}\n'
                '\t"%d"\n\t{\n\t\t"AccountName"\t\t"deck"\n\t\t"MostRecent"\t\t"1"\n\t\t"Timestamp"\t\t"1500000000"\n\t}\n}\n' % STEAMID)
    with open(root + "/userdata/%d/config/localconfig.vdf" % ACCOUNT, "w") as f:
        f.write('"UserLocalConfigStore"\n{\n\t"Software"\n\t{\n\t\t"Valve"\n\t\t{\n\t\t\t"Steam"\n\t\t\t{\n\t\t\t\t"Apps"\n\t\t\t\t{\n%s\t\t\t\t}\n\t\t\t}\n\t\t}\n\t}\n}\n' % apps_cfg)
    with open(root + "/userdata/%d/config/shortcuts.vdf" % ACCOUNT, "wb") as f:
        f.write(shortcuts_vdf(a.now))
    fav = {"id": "favorite", "name": "", "added": [4100020, 4100070], "removed": []}
    with open(root + "/userdata/%d/config/cloudstorage/cloud-storage-namespace-1.json" % ACCOUNT, "w") as f:
        json.dump([["user-collections.favorite", {"key": "user-collections.favorite", "timestamp": a.now,
                    "value": json.dumps(fav), "version": "1"}]], f)
    if a.art:
        cache = root + "/appcache/librarycache"
        for i, g in enumerate(GAMES[:7]):
            appid, name = g[0], g[1]
            color = PALETTE[i % len(PALETTE)]
            if i % 2 == 0:   # legacy flat names
                art("%s/%d_library_600x900.jpg" % (cache, appid), (300, 450), color, name)
                art("%s/%d_header.jpg" % (cache, appid), (460, 215), color, name)
                art("%s/%d_library_hero.jpg" % (cache, appid), (1920, 620), color, name, logo=False)
                logo_art("%s/%d_logo.png" % (cache, appid), name)
            else:            # per-app directory, hashed subfolder
                d = "%s/%d/%s" % (cache, appid, "a1b2c3d4e5")
                os.makedirs(d, exist_ok=True)
                art(d + "/library_600x900.jpg", (300, 450), color, name)
                art("%s/%d/header.jpg" % (cache, appid), (460, 215), color, name)
                art("%s/%d/library_hero.jpg" % (cache, appid), (1920, 620), color, name, logo=False)
                logo_art("%s/%d/logo.png" % (cache, appid), name)
        grid = root + "/userdata/%d/config/grid" % ACCOUNT
        u = SHORTCUTS[0][0] & 0xFFFFFFFF
        art("%s/%dp.png" % (grid, u), (300, 450), (90, 90, 100), SHORTCUTS[0][1])
        art("%s/%d.png" % (grid, u), (460, 215), (90, 90, 100), SHORTCUTS[0][1])
    print(root)


if __name__ == "__main__":
    main()
