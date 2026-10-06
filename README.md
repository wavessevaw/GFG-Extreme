<div align="center">

**English** · [Русский](README.ru.md)

<img src="docs/img/logo.png" alt="GFG Extreme" width="220">

# GFG Extreme Decky

**Press Run. Get smooth, efficient frames on Steam Deck.**

Frame generation, smart scaling and TDP savings, orchestrated for you by the **GFG Governor**.

![status](https://img.shields.io/badge/status-beta-fb0d00?style=flat-square)
![platform](https://img.shields.io/badge/Steam%20Deck-OLED%20%C2%B7%20LCD%20%C2%B7%20Dock-111?style=flat-square)
![decky](https://img.shields.io/badge/Decky%20Loader-plugin-111?style=flat-square)
![license](https://img.shields.io/badge/license-GPL--3.0-111?style=flat-square)

</div>

---

## Why it's great

Most frame-generation tools hand you a wall of switches and leave you to guess. **GFG Extreme Decky does the opposite: one beautiful screen and one Run button.**

| | |
|---|---|
| **One button** | Press **RUN**. The Governor reads your device, picks the target, starts the engine and manages it while you play. |
| **Knows your screen** | **Steam Deck OLED → 90 FPS**, **Steam Deck LCD → 60 FPS**, **Dock / external display → 60 FPS**. No manual tuning. |
| **Three modes** | **Battery** (lowest TDP first, 9 to 11 W ideal, real FPS stays at 24 or more), **Balanced** (starts at 45 real FPS and 12 W, never below 30 real FPS, never above your Deck's normal power range) and **Quality** (fewest generated frames first, then lowers TDP). Pick one on the home screen. |
| **Adapts all session** | Frame rate is checked every second: a starved game gets its watts back within about 2 s, and lower watts are tried every 45 s while the game holds. Multipliers run from native to ×3 in quarter steps (Battery may go deeper only as a last resort), confirmed on real renderer data and rolled back if they do not hold. |
| **Remembers your games** | Once a point has held, its operating point and TDP are stored per profile, display target and mode, and the next session starts there instead of searching. |
| **Sees the machine** | Temperature and its trend, GPU and busiest-CPU-core load, fan, battery draw and frametime (p95/p99, stutter) are read from the system. A one-line verdict (GPU-bound, CPU-bound, TDP-limited, hot, stuttering) is shown on Home. A CPU-bound game never gets render-scale points. |
| **Never touches your profile** | Your saved profile is **never modified**. The Governor works through a temporary overlay and always restores the original state. |
| **Safe by design** | No overclocking, no raising your power ceiling, never ×4/×5 automatically, and it backs off when another tool owns TDP or the pipeline. |
| **Honest effort rating** | **GFG Effort** (Easy · Medium · Hard · Nightmare) tells you how hard the engine is working, and is withheld until it's stable, so it doesn't flicker. |
| **Compact in-game overlay** | A single slim bar: FPS, frame time, multiplier, real → output FPS, render scale, TDP, battery time, effort. |
| **Everything is still there** | Profiles, per-game rules, Flatpak support, Pipeline Inspector, Configuration Journal and every engine option remain reachable under *Settings*. |

## A look inside

<div align="center">
<table>
<tr>
<td align="center"><img src="docs/img/home-idle-oled.png" width="250"><br><sub><b>Ready</b> · target picked for your screen</sub></td>
<td align="center"><img src="docs/img/home-locked-oled.png" width="250"><br><sub><b>Locked in</b> · real → ×2 → output, TDP, effort</sub></td>
<td align="center"><img src="docs/img/home-locked-lcd.png" width="250"><br><sub><b>LCD</b> · 60 FPS target, saving power</sub></td>
</tr>
</table>
</div>

> Screenshots are UI previews rendered with sample data in a mock Decky environment, not captures from a running Deck.

### In-game overlay

One compact line, top right, just the numbers that matter:

<div align="center">
<img src="docs/img/hud-ingame-standard.png" width="620">
</div>

`90 FPS  x2  (45)  sc100  9W  2h05  med`
(FPS with generated frames, multiplier, real FPS, render scale, TDP, time left, effort; MangoHud's own FPS and frame time appear only while the Governor has no renderer telemetry)

Choose **Minimal**, **Standard** or **Detailed**, and put it where you like. No CPU load clutter.

## How the Governor thinks

1. **Detect** the device (OLED, LCD, Dock) and choose the target.
2. **Remember**: if this game was played before in this mode, start from the point and TDP that held.
3. **Measure** the real frame rate from engine telemetry every second.
4. **Choose and confirm**: every operating point is **confirmed on real data** before it is kept and **rolled back** if it is not.
5. **Adapt**: add watts or a deeper ratio at once when the game falls short; try one watt less every 45 s while it holds.
6. **Release** everything cleanly on Stop, game exit or profile change. The Saved profile is never modified.

Every decision is written to a journal you can inspect.

## Something not working? Record a log

Settings → Diagnostics → **Check setup** tells in seconds whether the engine, launcher, overlay and TDP access are in place, and what to do about each missing piece. If the problem is during play: Settings → Diagnostics → **Record log**, play for a minute or two, **Stop and save log to Desktop**. A zip appears on the Steam Deck desktop, and the screen lists what the log shows (for example "no renderer diagnostics were written", "paused most of the time"). The zip contains `summary.txt`, a 1 Hz timeline, the renderer diagnostics, the Governor's decisions, a self-test of every precondition and the generated launcher. On a PC, `python3 tools/gfg_log_report.py <zip>` prints the same verdict.

## Targets

| Mode | Target |
|---|---|
| Steam Deck OLED | **90 FPS** |
| Steam Deck LCD | **60 FPS** (the panel tops out at 60 Hz) |
| Dock / external display | **60 FPS** |

## Install and use

Requires [Decky Loader](https://decky.xyz/) on SteamOS, and the **default public version** of [Lossless Scaling](https://store.steampowered.com/app/993090/Lossless_Scaling/) from Steam for frame generation or LS1 scaling.

1. Install the GFG Extreme Decky ZIP through Decky Loader.
2. Open GFG Extreme and select **Install engine** (the ZIP alone does not install it).
3. Set the Steam launch option of your game to:

```text
/home/deck/.local/bin/gfg %command%
```

4. Start the game and press **RUN**. GFG attaches to the running game; only a game started before this version (or without the launch command) needs one relaunch.

The old `mako-run` command keeps working as an alias. For Heroic, Lutris, EmuDeck and other Flatpak apps, open **Settings → System** and enable GFG for the app (it prepares the runtime extension and access for you).

## Everything else

- Per-game and per-process **profiles**, selected automatically by Steam app ID or process name.
- Frame generation through **GFG Engine**, **OptiScaler**, **Game Native** or **Off**, with Spatial Scaling and Shaders independent. External backends are **observe-only**, the Governor never fights them.
- **Pipeline Inspector**: compares *Saved*, *Effective*, *Governor runtime* and *Actual* launch state, verified against the live process.
- **Configuration Journal** with schema-safe restore.
- Gamescope WSI compatibility, MangoHud, bundled vkBasalt shaders (sharpening, anti-aliasing, lighting).
- Flatpak runtime extensions and per-app access.

## Status

**Beta (Governor v0.0.16).** The decision engine, overlay handling and safety rules are covered by an automated test suite (including tests that run the real generated launch wrapper in bash). No release has been validated on a real Steam Deck yet, so expect rough edges: please record a log and send it. Known limitations are listed in the release notes.

## Heritage and credits

GFG Extreme Decky is a **continuation of the MAKO and LSFG work**: it succeeds [Decky LSFG-VK Experimental](https://github.com/eugeniosegala/decky-lsfg-vk-experimental) under a separate product and package identity, and the bundled engine derives from the MAKO community project bringing LSFG frame generation, spatial scaling and shader effects to Linux. Huge thanks to the authors of MAKO and lsfg-vk.

GFG Extreme does not contain or distribute Lossless Scaling. Upstream `mako-*` filenames, Vulkan layer identifiers, configuration paths and RPC names are kept where changing them would break renderer compatibility.

## Documentation

[Governor architecture](docs/GFG_GOVERNOR_ARCHITECTURE.md) · [Telemetry capabilities](docs/GFG_TELEMETRY_CAPABILITIES.md) · [Known limitations](docs/GFG_GOVERNOR_KNOWN_LIMITATIONS.md) · [UI redesign notes](docs/GFG_UI_REDESIGN.md)

## Development

```bash
npm run test        # backend tests + frontend build + frontend smoke test
npm run build       # frontend/ → dist/index.js
npm run screenshots # re-render the UI previews
```

The interface source lives in [`frontend/`](frontend/) (no runtime npm dependencies, it uses the globals Decky provides). Licensed under GPL-3.0-or-later; see [LICENSE](LICENSE.md) and [third-party notices](THIRD_PARTY_NOTICES.md).
