<div align="center">

**English** · [Русский](README.ru.md)

<img src="docs/img/logo.png" alt="GFG Extreme" width="160">

# GFG Extreme

**Frame generation and automatic power management for Steam Deck.**<br>
A Decky Loader plugin: it generates frames up to your screen's refresh rate, picks the frame-generation ratio and the power limit for the game in front of it, and checks every change against the renderer's own data.

[**Download the latest release**](https://github.com/wavessevaw/GFG-Extreme/releases/latest) · [Install](#install) · [Modes](#modes) · [Extreme](#extreme) · [Troubleshooting](#troubleshooting)

![release](https://img.shields.io/github/v/release/wavessevaw/GFG-Extreme?style=flat-square&color=fb0d00&label=release)
![platform](https://img.shields.io/badge/Steam%20Deck-OLED%20%C2%B7%20LCD%20%C2%B7%20Dock-111?style=flat-square)
![decky](https://img.shields.io/badge/Decky%20Loader-plugin-111?style=flat-square)
![license](https://img.shields.io/badge/license-GPL--3.0-111?style=flat-square)

<br>

<img src="docs/img/card-overview.png" width="860">

<sub>The plugin in the Quick Access menu: Battery mode at work, Extreme mode, and the Details page. Rendered from the real interface with sample data.</sub>

</div>

---

## What it does

A Steam Deck OLED shows 90 frames per second. Most demanding games render far fewer. GFG Extreme fills the gap with generated frames and runs the APU at the lowest power that still holds the picture. For example, a game may render 30 real frames, GFG generates the rest up to 90, and the APU runs at 9 W instead of 15.

Press **Run** on the plugin's Home screen. From then on the Governor works on its own:

- **Target from the screen.** OLED → 90 FPS, LCD → 60 FPS, dock or external display → 60 FPS. If you lower the built-in screen's refresh rate, the target follows it.
- **Ratio and power together.** The Governor chooses how many frames to generate (×1 to ×3.75) and the TDP limit, for this game and this scene.
- **Every change is verified.** A new setting counts only once fresh renderer data confirms it, a lower render resolution only once the renderer reports the game really renders at it. Otherwise it is rolled back within seconds. Some games keep their full render size whatever is asked; GFG notices and stops trying lower resolutions there.
- **It keeps adjusting.** When a scene gets heavier, the Governor adds watts or generated frames within about two seconds. While the game holds, it looks for a lower setting again.
- **It remembers games.** The next session starts from what worked last time. **Settings → Diagnostics → Reset what GFG learned** starts one game from scratch.
- **It explains itself.** Home shows the real and output frame rates, the ratio, the TDP, what limits the game (GPU, CPU, power or heat) and how hard GFG is working. **Details** shows every decision.

Your saved profile is never modified. **Stop** returns everything to it.

Works with Steam games and, through Flatpak support, with Heroic, Lutris and emulators.

## Modes

<p align="center"><img src="docs/img/card-modes.png" width="860"></p>

| Mode | Real frames | Power | For |
|---|---|---|---|
| **Battery** | 24 or more | 9–11 W ideal, more only as a last resort | the longest play time |
| **Balanced** | 30 or more | starts at 12 W, never above the normal range | a steadier picture |
| **Quality** | as many as possible | lowered after quality is set | playing on the charger |
| **Extreme** | as many as the limit allows, 30 or more | the whole stock limit: 15 W or your lower limit | the most real frames on battery |

The mode is set per game profile and can be switched while the game runs.

## Extreme

<p align="center"><img src="docs/img/card-extreme.png" width="860"></p>

Battery and Balanced look for the lowest power a game tolerates. Extreme does the opposite: it spends the Deck's whole stock power limit on real frames. It works on a stock Deck: no overclocking, no BIOS changes.

- **One power ceiling.** 15 W, or your own lower limit from the Quick Access menu, never more. Every power write is clamped to it, Frame OS Act boosts included. If you change the limit while you play, the new value becomes the ceiling.
- **Render resolution as a trade.** Where it buys more real frames, Extreme renders at 90 % or 80 % and applies matched sharpening (0.15 at 90 %, 0.30 at 80 %). You can correct the sharpening by ±0.3 on Home. Lower resolution is never used in a CPU-bound game, never on top of your profile's own scaling, and sharpening is skipped when your vkBasalt filter already sharpens.
- **Confirmed or rolled back.** A new render scale counts only after the renderer reports the size the game actually renders at. Without that, the change is rolled back within 20 s. After two misses, Extreme stays at full resolution for the rest of the session.
- **One restart.** The scaler loads at game start. After switching a game to Extreme, restart it once to allow lower resolutions. Until then Extreme runs at full resolution and says so.
- **Frame OS Act on request.** The first switch to Extreme asks once whether Act may join. Leaving Extreme restores your previous Frame OS setting.

Home lists the nine directions Extreme is built around, each with its current state and the reason:

| Direction | In 1.6 |
|---|---|
| Render scale + sharpening | active when the renderer confirms it |
| CPU → GPU power split | active (the Smart power split below) |
| Frame OS Act | active after your consent, once the power is settled |
| Instant start | a remembered point per game, verified again at start |
| Quiet background | unavailable: Steam has no supported per-job API, and GFG never stops Steam |
| Cooling ahead | unavailable: no verified fan interface; stock fan control stays in charge |
| Memory tuning | unavailable: global memory settings are not changed without pressure and recovery tests |
| Low latency | unavailable: not measured on hardware yet |
| Stutter shield | unavailable: not validated on hardware yet |

The gain against Balanced is not shown as a number yet. It needs an A-B-A comparison on the same scene, which is planned. Averages from different sessions are not a comparison.

Battery and Balanced suggest Extreme when a game leaves part of the power limit unused.

## Smart power split

<p align="center"><img src="docs/img/card-power-split.png" width="390"></p>

The CPU and GPU of the Deck share one power limit. In a GPU-bound game the CPU still boosts to full clock between frames and takes watts the GPU could use. GFG lowers the CPU's maximum clock step by step and gives those watts to the GPU:

- **Only where it can help.** The game must be GPU-bound or at the power cap, and its busiest CPU core must keep room to spare at the lower clock.
- **Small steps.** 3.5 → 3.0 → 2.4 → 2.1 → 1.8 GHz, never below 1.6 GHz and never above your own limit. Each step is a 10-second trial.
- **Real frames first.** If real frames fall short or a core gets busy, the cap comes off at once. Loading screens, the Steam menu and Frame OS Act always run at full CPU clock.
- **Measured in your game.** Short A/B checks compare GPU clock per watt with and without the cap. A game with no measurable gain gets the split switched off.
- **Always returned.** Your CPU limit comes back when the game ends, on Stop and on unload, also after a crash. If another tool sets the CPU clock, GFG leaves it alone. Switch it off in **Details → Smart power split**.

## Frame OS (experimental)

<p align="center"><img src="docs/img/card-frame-os.png" width="740"></p>

Frame OS is a small Vulkan layer above the frame generator. It sees every real frame and your controller input, and adapts the real frame rate to the moment. Turn it on in **Settings → Diagnostics → Frame OS**; it loads at the next game start.

- **Observe** and **Shadow** only measure and show what Frame OS would do.
- **Act** changes frame timing and power (it needs an explicit unlock):
  - When you turn the camera or fight, it raises the real frame rate where the GPU can deliver it (for example ×3 → ×2, 45 real frames at 90 Hz).
  - In pauses and menus, it lowers the power limit.
  - It paces real frames so they wait less inside the frame generator (measured on a Deck: about 25 ms down to about 13 ms).
  - It rests while the Steam menu covers the game and hands control back when the APU gets hot or the output falls short.
- **Checked in your game.** In Act, Frame OS briefly switches one effect off and compares the same moment before, during and after (A-B-A). Home shows **Response**, **Frames** and **Energy** as measured values once three comparisons exist.
- **Remembered per game.** An effect that does not help in a game is switched off for that game and tried again every eight sessions.

## Filters

<p align="center"><img src="docs/img/card-filters.png" width="740"></p>

Shader filters (vkBasalt) on top of the game, chosen from the Quick Access menu:

- Eight looks, one tap each: Sharp (CAS), Vivid, HDR look, Cinema, Noir, Retro, Smooth (SMAA) or Off.
- Once filters are loaded, a new look applies in the running game. Filters load at game start; the card says when a restart is needed first.
- **Settings → Filters**: sharpening (CAS or DLS) and its strength, anti-aliasing (FXAA or SMAA), and 19 effects that run in the order you turn them on.
- Each game profile keeps its own look. Effects cost GPU time; with the Governor on, a heavy stack can mean slightly more power or a deeper ratio.

## In game and after the game

<p align="center"><img src="docs/img/hud-rings-standard.png" width="860"></p>

The in-game overlay shows the output FPS with the real frame rate under it, the TDP, battery time in Detailed, and the Frame OS rings when Frame OS is on. It refreshes once a second and is drawn by GFG's own Vulkan layer after the frame generator. In Flatpak apps and HDR games, and until the first restart after you pick the rings, a text line is shown instead:

`90 FPS  x3  (30)  sc100  TDP 9W  APU 8W  2h32  easy`

<p align="center"><img src="docs/img/card-session.png" width="740"></p>

When the game closes, Home sums up the session: average FPS, real frames and TDP, time per mode and Frame OS state, and the energy saved against your limit, in Wh from the measured draw and as minutes of battery. **Details** keeps your recent sessions. **Settings → In-game overlay** sets the style (rings or text), the detail level and the corner.

## Install

You need [Decky Loader](https://decky.xyz/) and [Lossless Scaling](https://store.steampowered.com/app/993090/Lossless_Scaling/) from Steam (the default public version).

1. Download the newest `GFG-Extreme-v*.zip` from [Releases](https://github.com/wavessevaw/GFG-Extreme/releases/latest) and install it in Decky with *Install from zip*. Accept the root access request: it is used only to write the power limit and the CPU clock cap.
2. Open GFG Extreme and tap **Install engine**.
3. In Steam, open the game's **Properties → Launch Options** and paste:
   ```text
   /home/deck/.local/bin/gfg %command%
   ```
   GFG shows this command with a **Copy** button while a game is not attached yet.
4. Start the game and press **Run**.

Heroic, Lutris, EmuDeck and other Flatpak apps: enable GFG for the app in **Settings → System**.

To update, install the new zip over the old one. Settings, profiles and what GFG learned are kept. Restart a running game so the new layers load.

## What GFG changes, and how it gives it back

- **Saved profile:** never written. The Governor works through a temporary overlay that the launcher reads only while the plugin runs.
- **Power limit:** owned only while a game runs under the Governor, never above the mode's ceiling, and restored on Stop, game exit and unload. If another tool changes it, GFG stops writing and does not restore over it.
- **CPU clock cap:** the same rules; a marker file restores your value after a crash.
- **No overclocking, no BIOS or firmware changes, no undervolting.**
- The root helper accepts only the power-limit and CPU-clock files, with checked value ranges.

## Troubleshooting

<p align="center"><img src="docs/img/card-help.png" width="740"></p>

1. **Settings → Diagnostics → Check setup** checks the engine, the launcher, the overlay, the diagnostics log and TDP access, and says what to fix for each failed item.
2. **Record a log:** Settings → Diagnostics → **Record log**, play for a minute or two, then **Stop**. A zip with a plain-language `summary.txt` lands on the Steam Deck desktop. [Open an issue](https://github.com/wavessevaw/GFG-Extreme/issues) and attach it.

## Status

The current release is **1.6**. Battery, Balanced and Quality are stable. Extreme is a first stage and has not been validated on many games yet. Frame OS is experimental and off unless you turn it on.

Every release passes an automated test suite (the Python backend, the generated launcher run in bash, the interface rendered in a headless browser). Logs from more games and setups help a lot. Known limitations: [docs/GFG_GOVERNOR_KNOWN_LIMITATIONS.md](docs/GFG_GOVERNOR_KNOWN_LIMITATIONS.md).

Recent versions:

- **1.6.2** Frame OS Act boosts only with GPU headroom; an honest "At the limit" for games heavier than the power allows.
- **1.6.1** Render scale counts only when the engine confirms it, in every mode; a faster guard.
- **1.6** Extreme mode with a single power ceiling, render scale with renderer confirmation, and an honest capability list.
- **1.5** Smart power split, filters on Home, a compact Home screen.
- **1.3** Frame OS checks its own effects in game and remembers every game.

Full notes: [Releases](https://github.com/wavessevaw/GFG-Extreme/releases).

<details>
<summary><b>More features</b></summary>

- Per-game profiles, picked automatically by Steam app ID or process name.
- Frame generation by **GFG Engine**, **OptiScaler**, **the game's own** or **Off**. Spatial scaling and vkBasalt shaders are independent of it. With an external backend GFG only watches.
- **Pipeline Inspector:** Saved vs. Effective vs. Governor vs. what the running process actually loaded.
- **Configuration Journal** with safe restore, and **All settings** for every engine option.
- Gamescope WSI compatibility, MangoHud, Flatpak runtime extensions and per-app access.

</details>

<details>
<summary><b>For developers</b></summary>

```bash
npm ci
npm test              # backend tests, frontend build, frontend smoke test
npm run build         # frontend/ → dist/index.js (CI fails if it is stale)
npm run screenshots   # re-render docs/img from the real interface
python3 tools/gfg_log_report.py <log.zip>   # read a recorded log on a PC
```

Docs: [Governor architecture](docs/GFG_GOVERNOR_ARCHITECTURE.md) · [Extreme foundation](docs/EXTREME_FOUNDATION.md) · [Telemetry](docs/GFG_TELEMETRY_CAPABILITIES.md) · [Interface](docs/GFG_UI_REDESIGN.md) · [Frame OS](docs/GFG_FRAME_OS.md). Every merge to `main` with a new version publishes a release automatically.

</details>

## Credits

GFG Extreme continues the **MAKO** and **lsfg-vk** work. It succeeds [Decky LSFG-VK Experimental](https://github.com/eugeniosegala/decky-lsfg-vk-experimental), and the bundled engine derives from the MAKO project, which brings LSFG frame generation, spatial scaling and shader effects to Linux. Thanks to their authors. GFG Extreme does not contain or distribute Lossless Scaling; upstream `mako-*` names are kept where renderer compatibility needs them.

GPL-3.0-or-later · [License](LICENSE.md) · [Third-party notices](THIRD_PARTY_NOTICES.md)
