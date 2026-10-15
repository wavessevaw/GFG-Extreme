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


def art(path, size, color, text):
    from PIL import Image, ImageDraw, ImageFont
    w, h = size
    img = Image.new("RGB", size)
    d = ImageDraw.Draw(img)
    for y in range(h):
        t = y / max(1, h - 1)
        d.line([(0, y), (w, y)], fill=tuple(int(c * (1 - 0.75 * t) + 10 * t) for c in color))
    for i in range(0, w + h, 46):
        d.line([(i, 0), (i - h, h)], fill=tuple(min(255, c + 25) for c in color), width=6)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", max(16, min(w // 12, h // 6)))
    except OSError:
        font = ImageFont.load_default()
    d.text((w // 14, h - h // 4), text, fill=(255, 255, 255), font=font)
    img.save(path)


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
                art("%s/%d_library_hero.jpg" % (cache, appid), (960, 310), color, name)
            else:            # per-app directory, hashed subfolder
                d = "%s/%d/%s" % (cache, appid, "a1b2c3d4e5")
                os.makedirs(d, exist_ok=True)
                art(d + "/library_600x900.jpg", (300, 450), color, name)
                art("%s/%d/header.jpg" % (cache, appid), (460, 215), color, name)
                art("%s/%d/library_hero.jpg" % (cache, appid), (960, 310), color, name)
        grid = root + "/userdata/%d/config/grid" % ACCOUNT
        u = SHORTCUTS[0][0] & 0xFFFFFFFF
        art("%s/%dp.png" % (grid, u), (300, 450), (90, 90, 100), SHORTCUTS[0][1])
        art("%s/%d.png" % (grid, u), (460, 215), (90, 90, 100), SHORTCUTS[0][1])
    print(root)


if __name__ == "__main__":
    main()
