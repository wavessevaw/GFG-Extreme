# GFG Extreme 3.2.x: independent test brief

**Maintainer:** GFG Team  
**Platform:** Steam Deck / SteamOS  
**Current release when this note was prepared:** [v3.2.1](https://github.com/wavessevaw/GFG-Extreme/releases/tag/v3.2.1) (GSF Kedavra 1.4.1)  
**Source:** [GFG Extreme](https://github.com/wavessevaw/GFG-Extreme) · [GSF Kedavra](https://github.com/wavessevaw/GSF_Kedavra)  
**License:** GPL-3.0-or-later, subject to the included third-party licenses

## What the project implements

GFG Extreme is a Decky Loader plugin combining two components:

- **GSF Kedavra:** frame reconstruction with Vulkan GPU processing and presentation scheduling integrated into a modified Gamescope compositor. The architecture targets intermediate-frame insertion without a Lossless Scaling dependency.
- **Governor / Autopilot:** feedback-based performance and power control, with measured trials, rollback conditions, and per-game state.

The intended operating points include ×2 and ×3 on the Steam Deck OLED 90 Hz display, and compatible modes at other refresh rates. Generated output FPS is not equivalent to real game FPS or measured display latency.

The plugin installs a custom Gamescope component and requires a reboot. See the [installation and recovery notes](../README.md#installation) before testing; do not assume this modifies only the Decky user interface.

## Evidence boundary

The [v3.2.1 release notes](https://github.com/wavessevaw/GFG-Extreme/releases/tag/v3.2.1) describe scheduler *simulation* results and a border-reconstruction test on lavapipe. These results are not independent measurements of frame delivery, input-to-display latency, or battery-life gains on physical Steam Deck hardware.

Compatibility across games, SteamOS builds, HDR modes, and Proton configurations remains a test question. We are seeking independent reproductions, including negative results.

## Suggested A/B protocol

1. Record the Steam Deck model (LCD/OLED), SteamOS build, game, Proton version, display refresh, and graphics settings.
2. Use a reproducible scene and keep the refresh rate, frame cap, thermal state, and graphics preset constant.
3. Collect a **stock compositor** baseline.
4. Collect a **modified Gamescope with generation disabled** baseline, where the build permits this.
5. Collect generation-enabled runs at **×2**, then **×3**, separately. Note any changes made by Governor / Autopilot.
6. Report real FPS, generated/output cadence, frame-time percentiles, missed refresh deadlines, GPU analysis/generation cost, APU power, and any visible artifacts. Include measurement source and recording duration.
7. If available, add an external high-speed video or latency measurement. Software-reported output FPS alone cannot establish optical delivery or end-to-end latency.
8. Record recovery after exiting a game and after disabling/removing the modified component. Stop testing if Gaming Mode becomes unstable.

Logs, short capture clips, and reports of failures are more useful than unrepeatable best-case FPS screenshots. If a metric is unavailable, mark it **not measured** rather than estimating it.

## Reporting format

| Field | Value |
|---|---|
| Deck model / SteamOS version | |
| GFG Extreme / GSF Kedavra version | |
| Game / Proton version / scene | |
| Display Hz / real FPS cap | |
| Generation setting, Governor mode | |
| Stock baseline | |
| Modified compositor, FG disabled | |
| Modified compositor, FG enabled | |
| Real FPS / output FPS / P95 / P99 | |
| GPU generation and analysis time | |
| APU power / temperatures | |
| Visual artifacts / stalls / input latency | |
| Logs, video, reproduction steps | |
| Recovery / rollback result | |

## Contact

Reports and technical corrections: [GitHub Issues](https://github.com/wavessevaw/GFG-Extreme/issues) or the [GFG Extreme Telegram community](https://t.me/gfg_extreme). For editorial contacts, refer to the linked source, release notes, and measured limitations rather than marketing claims.

**GFG Team**
