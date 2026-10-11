<div align="center">

**English** · [Русский](README.ru.md)

<img src="docs/img/logo.png" alt="GFG Extreme" width="144">

# GFG Extreme

**Frame generation and adaptive power management for Steam Deck**

A Decky Loader plugin that measures real and generated frame cadence, adjusts the Governor's TDP budget, and explains what the active game is doing.

[**Download 2.0.0**](https://github.com/wavessevaw/GFG-Extreme/releases/tag/v2.0.0) · [Install](#installation) · [Autopilot](#autopilot) · [Diagnostics](#diagnostics)

![Release](https://img.shields.io/github/v/release/wavessevaw/GFG-Extreme?style=flat-square&color=fb0d00&label=release)
![Steam Deck](https://img.shields.io/badge/Steam%20Deck-OLED%20%7C%20LCD-20242e?style=flat-square)
![Decky](https://img.shields.io/badge/Decky%20Loader-plugin-20242e?style=flat-square)
![License](https://img.shields.io/badge/license-GPL--3.0-20242e?style=flat-square)

<img src="docs/img/card-overview.png" alt="GFG Extreme 2.0.0 user interface: Battery, Autopilot and Details" width="900">

<sub>Real GFG Extreme 2.0.0 interface rendered in a browser using illustrative sample data. Not measured game performance.</sub>

</div>

## What is new in 2.0.0?

**Autopilot replaces the old Extreme mode.** Saved profiles formerly using Extreme are migrated to Autopilot; their saved renderer settings are not overwritten.

- **One decision-maker.** Autopilot plans; the existing Governor alone controls TDP. No competing power writer.
- **Evidence-based frame targets.** The goal follows the display (up to 90 Hz on OLED, 60 Hz on LCD; external displays follow detected capabilities). On a 90 Hz panel, Autopilot can provisionally switch its output target from 90 to 60 when fresh, non-overlapping measurements prove it cannot hold 90, and cautiously retry later.
- **Measured power search.** The Governor tries a lower wattage only with sufficient evidence, verifies the renderer and rolls back a failed point. Repeated failed TDP floors can be blocked for up to **30 minutes**, including after a restart.
- **Steam GPU Clock trials.** For a probable CPU bottleneck, Autopilot may try a small reduction to the manual GPU clock ceiling through the SteamOSManager Quick Access Menu interface. It checks read-back and FPS/frametime/power measurements; it does not overwrite a player's manual clock, and restores GFG-owned settings.
- **Optional Half Rate Shading.** Per-game opt-in tests Steam's RADV 2×2 VRS setting where supported, comparing fresh measurements and restoring it if the trial fails. This can blur text, HUD and fine details. It affects game shading, **not only generated intermediate frames**.
- **One experiment at a time.** GPU Clock and shading do not start while the Steam menu covers the game, without a confirmed operating point, or during another active trial. A *proposed* experiment is not shown as *applied*.
- **Clear telemetry.** Real FPS, output FPS, CPU/GPU activity, temperature, GPU MHz, APU draw and real frametime inform decisions and the HUD. Output FPS is a renderer estimate, **not proof of distinct frames actually displayed**.

<div align="center">
<img src="docs/img/card-autopilot.png" alt="Actual Autopilot card with a confirmed and a deferred decision" width="800">
<sub>Autopilot's actual cards. Sample values; no FPS or battery-life gain implied.</sub>
</div>

## Modes

<div align="center"><img src="docs/img/card-modes.png" alt="Battery, Balanced, Quality, Autopilot" width="900"></div>

| Mode | Priority | How it works |
| --- | --- | --- |
| **Battery** | Efficiency | Searches lower TDP first; targets at least 24 real FPS in normal operating points where achievable |
| **Balanced** | Consistency | Starts near 12 W and normally targets at least 30 real FPS |
| **Quality** | Real-frame quality | Prefers fewer generated frames, then looks for watt savings |
| **Autopilot** | Adaptive balance | Selects a realistic output target, keeps Governor TDP control, and selectively evaluates GPU Clock / opt-in shading |

Performance depends on the game, scene, rendering backend, refresh rate and power limits. These are strategies, not guaranteed frame-rate floors.

## In-game overlay

<div align="center">
<img src="docs/img/hud-rings-standard.png" alt="Autopilot HUD rings for real and output FPS, power and host telemetry" width="900">
<sub>The actual GFG HUD bitmap on an illustrative background; sample measurements, not a capture of game performance.</sub>
</div>

The optional Vulkan rings overlay shows output and real FPS, TDP, and additional Autopilot metrics where available. Missing or stale readings are shown as unavailable rather than green. Configure style, detail and position in **Settings → In-game overlay**. In cases where the rings cannot load, GFG uses a text-line fallback.

## Other features

GFG Extreme 2.0.0 still includes the earlier Governor work, alongside the new Autopilot:

- **Per-game profiles**, remembered viable operating points and explicit reset of learned game data.
- **Smart CPU/GPU power split**, which can trial a CPU cap in a GPU-bound game and restore it if measured performance worsens. Available only where the OS permits safe control.
- **Frame OS** with Observe, Shadow and optional experimental Act. The Act path has not been proven to improve each game; it can yield or roll back when unstable.
- **vkBasalt filters** for sharpening, anti-aliasing and color looks; game restarts may be required for initial layer loading.
- **Session summaries and Diagnostics**, including recent FPS/frametime/power estimates, reasons for Governor decisions and exportable logs.

<div align="center">
<img src="docs/img/card-power-split.png" alt="CPU/GPU power split details" width="390">
<img src="docs/img/card-frame-os.png" alt="Frame OS information" width="740">
<img src="docs/img/card-filters.png" alt="Shader filters" width="740">
</div>

## Installation

Requires [Decky Loader](https://decky.xyz/) and [Lossless Scaling on Steam](https://store.steampowered.com/app/993090/Lossless_Scaling/) for the supported GFG generation setup.

1. Download [**GFG-Extreme-v2_0_0.zip**](https://github.com/wavessevaw/GFG-Extreme/releases/download/v2.0.0/GFG-Extreme-v2_0_0.zip). Use Decky's **Install from zip** feature and approve the requested permissions for supported power controls.
2. Open GFG Extreme and select **Install engine** if it is not installed.
3. For a Steam game, open **Properties → Launch Options** and add:

   ```text
   /home/deck/.local/bin/gfg %command%
   ```

4. Restart the game to load the renderer and Vulkan layers, then press **Run** in the plugin.

For Heroic, Lutris, EmuDeck and other Flatpak apps, check **Settings → System** for the supported integration and permissions. Installing a newer Decky ZIP over the old one preserves your settings and learned data.

## Restoring settings and safety

The Governor uses a temporary runtime overlay and does not rewrite the Saved game profile. GFG-owned TDP, GPU Clock, Half Rate Shading and CPU caps are restored on Stop, game exit and mode changes. If restoring cannot be verified, the affected experiment stays blocked while recovery is pending. Changes made manually in Steam QAM take priority over GFG's own settings.

**No overclocking, BIOS modification or undervolting is required.** SteamOSManager features can be unavailable on some firmware, in which case the corresponding Autopilot action is disabled.

## Diagnostics

<div align="center"><img src="docs/img/card-help.png" alt="Setup check and diagnostic log" width="800"></div>

Go to **Settings → Diagnostics → Check setup** to check the renderer, launcher, overlay and power-control access. To report a problem, select **Record log**, reproduce the issue in game, and stop recording. Attach the exported ZIP to a [GitHub issue](https://github.com/wavessevaw/GFG-Extreme/issues). For game-specific changes, include the display refresh rate and whether Steam QAM was open.

## Status and limitations

**Official software release: 2.0.0 (11 October 2026).** Backend, frontend and mock Vulkan-layer tests, plus Decky ZIP integrity checks, pass in CI. This **does not** imply Steam Deck LCD/OLED hardware validation of dynamic GPU Clock or Half Rate Shading. Generated-frame acquisition timeouts and Frame OS Act gains need independent device testing. Allow Tearing is not automatically controlled.

Measured output cadence is not the same as optical frame delivery. The 60/90 target transition on OLED, visual quality with VRS and physical restore behavior must be checked in games before performance or battery claims.

[Official release notes](RELEASE_DESCRIPTION_V2_0_0.md) · [Known limitations](docs/GFG_GOVERNOR_KNOWN_LIMITATIONS.md) · [Autopilot acceptance](docs/AUTOPILOT_ACCEPTANCE.md)

<details>
<summary><b>Developers and documentation</b></summary>

```bash
npm ci
npm test
npm run screenshots       # render genuine UI cards + ring HUD images
python3 tools/gfg_log_report.py <log.zip>
```

Architecture: [Governor](docs/GFG_GOVERNOR_ARCHITECTURE.md) · [Telemetry](docs/GFG_TELEMETRY_CAPABILITIES.md) · [Frame OS](docs/GFG_FRAME_OS.md).

</details>

## Credits

GFG Extreme continues work from [MAKO](https://github.com/eugeniosegala/MAKO) and lsfg-vk. It succeeds [Decky LSFG-VK Experimental](https://github.com/eugeniosegala/decky-lsfg-vk-experimental). It does not include or redistribute Lossless Scaling.

Community: https://t.me/gfg_extreme

GPL-3.0-or-later · [License](LICENSE.md) · [Third-party notices](THIRD_PARTY_NOTICES.md)
