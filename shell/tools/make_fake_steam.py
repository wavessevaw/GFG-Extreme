#!/usr/bin/env python3
"""Build a fake Steam install tree for GFG Shell tests and screenshots.

Every name and app id here is fictional. Layout mirrors the files GFG Shell reads:
libraryfolders.vdf (two libraries), appmanifest_*.acf (installed, not installed, a
Proton tool that must be hidden), loginusers.vdf, localconfig.vdf, binary
shortcuts.vdf (one appid with the sign bit set, one legacy entry without an appid),
Steam favorites/hidden JSON, artwork in both the legacy flat and the per-app
librarycache layouts, and a binary appcache/appinfo.vdf (v29 by default; v28 and v27
copies are written next to the tree for the parser tests) that adds owned games that
are not installed plus DLC/tools/soundtracks that must stay hidden.

usage: make_fake_steam.py <out_dir> [--art] [--now <unix>] [--appinfo-format 27|28|29]
       make_fake_steam.py --synthetic-appinfo <file> [--mb 50] [--appinfo-format 29]
         (benchmark input: ~50 MB of realistic-looking app entries)
"""
import argparse
import hashlib
import json
import os
import random
import struct
import time
import zlib

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
    (4100090, "Protonaut", 1, 4, None, 0, 3_000_000_000),     # a game whose name starts with "Proton"
]
# Installed manifest without a "name" (Steam writes these while appinfo is not yet known):
# the name comes from appinfo.vdf, else from installdir.
NAMELESS = [(4100100, "EmberTrail"), (4100105, "Kite Valley")]
# appinfo.vdf entries: appid, name, type, owned-by ("cache" = appcache/librarycache/<id>/,
# "flat" = legacy flat librarycache art, "play" = localconfig playtime, None = not owned)
APPINFO = [
    (4100010, "Neon Drift", "game", "cache"),            # installed: the manifest copy wins
    (4100060, "Glass Cathedral", "game", "cache"),       # manifest (not installed) wins, no duplicate
    (4100100, "Ember Trail", "game", None),              # name for the nameless manifest
    (4100110, "Frost Signal", "game", "cache"),          # owned, not installed -> listed
    (4100120, "Lumen Tactics", "Game", "play"),          # owned (played), not installed -> listed
    (4100125, "Paper Comet", "game", "flat"),            # owned (legacy flat art) -> listed
    (4100130, "Neon Drift Soundtrack", "music", "cache"),
    (4100140, "Neon Drift: Night Pack", "DLC", "cache"),
    (4100150, "Foundry Map Editor", "Tool", "cache"),
    (4100160, "Frost Signal Demo", "demo", "cache"),
    (4100165, "Orbital Foundry Server", "application", "cache"),
    (4100170, "Not Owned Game", "game", None),           # in appinfo only: not in the library
    (4100180, "Hidden Relic", "game", "cache"),          # owned but in Steam's Hidden collection
    (1493710, "Proton Experimental", "Tool", None),
    (4100090, "Protonaut", "game", None),
]
SHORTCUTS = [  # signed int32 appid as Steam stores it
    (-1820446516, "Retro Arcade Hub", "/home/deck/Emu/arcade.sh", 3),
    (2081234567, "Indie Sketchbook", "/home/deck/Games/sketch/run.sh", None),
    (-1000000001, "GFG Shell", "/home/deck/.local/share/gfg-shell/gfg-shell.sh", None),  # must be hidden
    (None, "Old Shortcut", "/home/deck/Games/old/start.sh", None),   # pre-2019 entry: no appid field
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
        if appid is not None:
            out += bin_int("appid", appid)
        out += bin_str("AppName", name) + bin_str("Exe", '"%s"' % exe)
        out += bin_str("StartDir", os.path.dirname(exe)) + bin_str("icon", "") + bin_str("LaunchOptions", "")
        out += bin_int("IsHidden", 0) + bin_int("LastPlayTime", now - days * 86400 if days is not None else 0)
        out += b"\x00tags\x00\x08"   # empty tags map
        out += b"\x08"
    return out + b"\x08\x08"


def legacy_shortcut_appid(exe, name):
    """Steam's id for a shortcut without an appid field: crc32(exe + name) | 0x80000000."""
    return (zlib.crc32(('"%s"' % exe + name).encode()) & 0xFFFFFFFF) | 0x80000000


# --- binary appinfo.vdf -------------------------------------------------------
APPINFO_MAGIC = {27: 0x07564427, 28: 0x07564428, 29: 0x07564429}


class KV:
    """Binary KeyValues writer; v29 writes keys as int32 indices into a string table."""
    def __init__(self, version, table):
        self.v, self.table = version, table

    def key(self, k):
        if self.v >= 29:
            if k not in self.table:
                self.table[k] = len(self.table)
            return struct.pack("<i", self.table[k])
        return k.encode() + b"\x00"

    def node(self, d):
        out = b""
        for k, v in d.items():
            if isinstance(v, dict):
                out += b"\x00" + self.key(k) + self.node(v)
            elif isinstance(v, int):
                out += b"\x02" + self.key(k) + struct.pack("<i", v)
            else:
                out += b"\x01" + self.key(k) + str(v).encode() + b"\x00"
        return out + b"\x08"


def app_tree(appid, name, typ, rnd=None):
    common = {"name": name, "type": typ, "parent": "0", "oslist": "windows,linux",
              "associations": {"0": {"type": "developer", "name": "Fictional Studio"}},
              "small_capsule": {"english": "capsule_231x87.jpg", "russian": "capsule_231x87_russian.jpg"},
              "gameid": appid}
    tree = {"appinfo": {"appid": appid, "common": common,
                        "extended": {"developer": "Fictional Studio", "homepage": "https://example.invalid/"},
                        "config": {"installdir": name.replace(" ", ""), "launch": {"0": {"executable": "game.exe"}}}}}
    if rnd is not None:   # benchmark: realistic bulk (depots, languages) after "common"
        tree["appinfo"]["depots"] = {str(appid + i): {"manifests": {"public": {"gid": str(rnd.getrandbits(62)),
                                     "size": str(rnd.getrandbits(34))}}, "config": {"oslist": "windows"}}
                                     for i in range(1, rnd.randint(2, 18))}
        common["languages"] = {l: 1 for l in ("english", "russian", "german", "french", "spanish", "japanese")}
        common["category"] = {"category_%d" % rnd.randint(1, 60): 1 for _ in range(rnd.randint(3, 15))}
    return tree


def appinfo_vdf(version, apps):
    """apps: iterable of (appid, tree). Returns the whole file as bytes."""
    table = {}
    kv = KV(version, table)
    parts = []
    for appid, tree in apps:
        data = kv.node(tree)
        sha = hashlib.sha1(data).digest()
        head = struct.pack("<IIQ", 2, 1700000000, 0) + sha + struct.pack("<I", 12345)
        if version >= 28:
            head += hashlib.sha1(data).digest()
        parts.append(struct.pack("<II", appid, len(head) + len(data)) + head + data)
    parts.append(struct.pack("<I", 0))
    body = b"".join(parts)
    if version >= 29:
        header_len = 16
        strings = b"".join(k.encode() + b"\x00" for k, _ in sorted(table.items(), key=lambda kv2: kv2[1]))
        return (struct.pack("<IIq", APPINFO_MAGIC[29], 1, header_len + len(body)) + body
                + struct.pack("<I", len(table)) + strings)
    return struct.pack("<II", APPINFO_MAGIC[version], 1) + body


def synthetic_appinfo(path, mb, version):
    """Benchmark file: ~mb MB of entries, appids 10..; real-looking key mix."""
    rnd = random.Random(7)
    target, apps, appid = mb * 1_000_000, [], 10
    sizer = KV(version, {})
    size = 0
    types = ["game"] * 5 + ["dlc"] * 6 + ["tool", "application", "demo", "music", "config"]
    while size < target:
        tree = app_tree(appid, "Synthetic App %d" % appid, rnd.choice(types), rnd)
        size += len(sizer.node(tree)) + 68
        apps.append((appid, tree))
        appid += 10
    data = appinfo_vdf(version, apps)
    with open(path, "wb") as f:
        f.write(data)
    print("%s: %d apps, %.1f MB" % (path, len(apps), len(data) / 1e6))


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
    ap.add_argument("out", nargs="?")
    ap.add_argument("--art", action="store_true")
    ap.add_argument("--now", type=int, default=int(time.time()))
    ap.add_argument("--appinfo-format", type=int, choices=(27, 28, 29), default=29)
    ap.add_argument("--synthetic-appinfo")
    ap.add_argument("--mb", type=int, default=50)
    a = ap.parse_args()
    if a.synthetic_appinfo:
        synthetic_appinfo(a.synthetic_appinfo, a.mb, a.appinfo_format)
        return
    if not a.out:
        ap.error("out directory required")
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
    # A stale copy of the SD-card game left in the internal library (Steam moved it):
    # the installed copy must win even though the internal library is scanned first.
    with open(libs[0] + "/steamapps/appmanifest_4100020.acf", "w") as f:
        f.write(acf(4100020, "Пепел Севера", 2, 0, "PepelSevera"))
    for appid, installdir in NAMELESS:
        os.makedirs(libs[0] + "/steamapps/common/" + installdir, exist_ok=True)
        with open(libs[0] + "/steamapps/appmanifest_%d.acf" % appid, "w") as f:
            f.write(acf(appid, "", 4, 1_000_000, installdir).replace('\t"name"\t\t""\n', ""))
    for appid, name, typ, owned in APPINFO:
        if owned == "play":
            apps_cfg += '\t\t\t\t\t"%d"\n\t\t\t\t\t{\n\t\t\t\t\t\t"LastPlayed"\t\t"%d"\n\t\t\t\t\t\t"Playtime"\t\t"%d"\n\t\t\t\t\t}\n' % (
                appid, a.now - 90 * 86400, 640)
    # an entry Steam keeps for every app with cloud/launch settings: no play history, not a signal
    apps_cfg += '\t\t\t\t\t"4100170"\n\t\t\t\t\t{\n\t\t\t\t\t\t"cloud"\n\t\t\t\t\t\t{\n\t\t\t\t\t\t\t"last_sync_state"\t\t"synchronized"\n\t\t\t\t\t\t}\n\t\t\t\t\t}\n'
    with open(root + "/config/loginusers.vdf", "w") as f:
        f.write('"users"\n{\n\t"76561198000000001"\n\t{\n\t\t"AccountName"\t\t"old"\n\t\t"MostRecent"\t\t"0"\n\t\t"Timestamp"\t\t"1600000000"\n\t}\n'
                '\t"%d"\n\t{\n\t\t"AccountName"\t\t"deck"\n\t\t"MostRecent"\t\t"1"\n\t\t"Timestamp"\t\t"1500000000"\n\t}\n}\n' % STEAMID)
    with open(root + "/userdata/%d/config/localconfig.vdf" % ACCOUNT, "w") as f:
        f.write('"UserLocalConfigStore"\n{\n\t"Software"\n\t{\n\t\t"Valve"\n\t\t{\n\t\t\t"Steam"\n\t\t\t{\n\t\t\t\t"Apps"\n\t\t\t\t{\n%s\t\t\t\t}\n\t\t\t}\n\t\t}\n\t}\n}\n' % apps_cfg)
    with open(root + "/userdata/%d/config/shortcuts.vdf" % ACCOUNT, "wb") as f:
        f.write(shortcuts_vdf(a.now))
    fav = {"id": "favorite", "name": "", "added": [4100020, 4100070], "removed": []}
    hidden = {"id": "hidden", "name": "", "added": [4100180], "removed": []}
    with open(root + "/userdata/%d/config/cloudstorage/cloud-storage-namespace-1.json" % ACCOUNT, "w") as f:
        json.dump([["user-collections.favorite", {"key": "user-collections.favorite", "timestamp": a.now,
                    "value": json.dumps(fav), "version": "1"}],
                   ["user-collections.hidden", {"key": "user-collections.hidden", "timestamp": a.now,
                    "value": json.dumps(hidden), "version": "1"}]], f)
    # appinfo.vdf in the requested format, plus every format next to the tree for parser tests
    trees = [(appid, app_tree(appid, name, typ)) for appid, name, typ, _ in APPINFO]
    with open(root + "/appcache/appinfo.vdf", "wb") as f:
        f.write(appinfo_vdf(a.appinfo_format, trees))
    for v in (27, 28, 29):
        with open(os.path.join(a.out, "appinfo_v%d.vdf" % v), "wb") as f:
            f.write(appinfo_vdf(v, trees))
    with open(os.path.join(a.out, "appinfo_truncated.vdf"), "wb") as f:
        f.write(appinfo_vdf(29, trees)[:900])           # cut inside an entry, string table lost
    cache = root + "/appcache/librarycache"
    for appid, name, typ, owned in APPINFO:
        if owned == "cache":
            os.makedirs("%s/%d" % (cache, appid), exist_ok=True)
        elif owned == "flat" and not a.art:
            with open("%s/%d_icon.jpg" % (cache, appid), "wb") as f:
                f.write(b"")                            # Steam's legacy flat icon name; content unused
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
        for i, appid in enumerate((4100110, 4100125)):   # owned, not installed
            name = [x[1] for x in APPINFO if x[0] == appid][0]
            color = PALETTE[(i + 3) % len(PALETTE)]
            if appid == 4100125:
                art("%s/%d_library_600x900.jpg" % (cache, appid), (300, 450), color, name)
                art("%s/%d_header.jpg" % (cache, appid), (460, 215), color, name)
            else:
                art("%s/%d/library_600x900.jpg" % (cache, appid), (300, 450), color, name)
                art("%s/%d/library_hero.jpg" % (cache, appid), (1920, 620), color, name, logo=False)
        grid = root + "/userdata/%d/config/grid" % ACCOUNT
        u = SHORTCUTS[0][0] & 0xFFFFFFFF
        art("%s/%dp.png" % (grid, u), (300, 450), (90, 90, 100), SHORTCUTS[0][1])
        art("%s/%d.png" % (grid, u), (460, 215), (90, 90, 100), SHORTCUTS[0][1])
    print(root)


if __name__ == "__main__":
    main()
