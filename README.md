<div align="center">

**English** · [Русский](README.ru.md)

<img src="docs/img/logo.png" alt="GFG Extreme" width="144">

# GFG Extreme

**Coordinated frame generation, performance and power management for Steam Deck**

A Decky Loader plugin that coordinates the frame generator, CPU/GPU resources, rendering workload and power limits. Autopilot observes each game and chooses measurable, reversible adjustments rather than changing only TDP.

[**Download 2.1.5**](https://github.com/wavessevaw/GFG-Extreme/releases/tag/v2.1.5) · [Install](#installation) · [Autopilot](#autopilot) · [Diagnostics](#diagnostics)

![Release](https://img.shields.io/github/v/release/wavessevaw/GFG-Extreme?style=flat-square&color=fb0d00&label=release)
![Steam Deck](https://img.shields.io/badge/Steam%20Deck-OLED%20%7C%20LCD-20242e?style=flat-square)
![Decky](https://img.shields.io/badge/Decky%20Loader-plugin-20242e?style=flat-square)
![License](https://img.shields.io/badge/license-GPL--3.0-20242e?style=flat-square)

<img src="docs/img/card-overview.png" alt="GFG Extreme 2.1.2 user interface: Battery, Autopilot and Details" width="900">

<sub>Real GFG Extreme 2.1.2 interface rendered in a browser using illustrative sample data. Not measured game performance.</sub>

</div>

## Autopilot

**Autopilot in GFG Extreme 2.1.5 is not an automatic TDP slider.** It is an orchestration mode that balances frame pacing, genuinely rendered frames, generated output, visual workload, APU power and temperature. Watts are only one of its tools.

The existing Governor handles a *rendering operating point*: the required real-frame cadence, generation multiplier, and available power. **Autopilot sits above the Governor.** It inspects the game, selects a promising type of intervention, reserves that resource for an isolated trial, and checks whether the result was worthwhile. It avoids adjusting several unrelated knobs simultaneously and then pretending to know which one helped.

### What it can control and coordinate

| Resource / tool | Purpose | What actually changes |
| --- | --- | --- |
| **Target FPS** | Choose an achievable output goal rather than endlessly chasing unreachable 90 FPS | On a 90 Hz display, may provisionally lower the software output target to 60 using fresh, non-overlapping evidence windows, then cautiously retry 90 |
| **Frame generation** | Balance the share of real and generated frames | Via Governor, selects operating points and multipliers from ×1 to ×3; ×3.25–×3.75 only when needed, ×4 reserved for emergency fallback. Within 8 % of the FPS target counts as on target |
| **APU power / TDP** | Preserve cadence at lower energy or help a heavier scene | Governor searches, confirms and rolls back power limits. Repeated failing lower-power steps can be blocked for up to 30 minutes |
| **Steam GPU Clock** | Test whether the GPU ceiling is unhelpful when the CPU appears to be the bottleneck | Attempts one downward GPU clock-ceiling step via SteamOSManager, confirms read-back and checks fresh performance data |
| **CPU/GPU power split** | Reallocate shared APU headroom toward a busy GPU | The separate Smart Power Split module may trial a CPU maximum-frequency cap with measured rollback; Autopilot coordinates pauses to prevent conflicting resource trials |
| **Render Scale / Flow Scale** | Reduce game-rendering or generated-frame workload where supported | Governor can use renderer-confirmed 90% / 80% scale steps; the separate experimental automatic Flow controller can trial generator workload when no conflicting intervention is active |
| **Half Rate Shading** | Trial a lower cost for GPU shading | When supported and enabled for the profile, trials Steam RADV VRS from 1×1 to 2×2, measures and rolls back when the experiment fails |
| **Thermal/ownership guard** | Avoid unsafe or misleading changes | Pauses on high temperature, missing data or Steam QAM/manual overrides, and blocks overlapping experiments |
| **Telemetry and HUD** | Expose what is measured and why action is taken | Shows Real/Output FPS, CPU/GPU utilization, GPU MHz, real-frame timing, temperature, TDP and trial state |

Smart Power Split, Flow Scale, Frame OS Act and compatible shading trials default on. Autopilot coordinates them and pauses incompatible trials. Explicit saved off choices remain off. Act prepares input-responsive pacing; Boost and Fusion execute only in Autopilot. vkBasalt looks retain the selected filter configuration.

### How its decision loop works

1. **Observe the actual game.** Collect fresh Real FPS and Output FPS, p95/p99 *real*-frame timing, GPU MHz and load, the busiest CPU core, temperature, APU draw and power-cap status. An Output FPS reading of 90 does not prove 90 real frames or 90 distinct optically verified screen updates.
2. **Choose the goal and operating point.** Account for refresh rate, renderer capabilities, the real-frame cadence needed by the chosen multiplier and the power available. When a scene becomes harder, Governor can choose a deeper generation step before simply spending more watts.
3. **Diagnose the likely constraint.** A saturated GPU points toward the power budget or an enabled shading trial. High CPU utilization with lower GPU utilization may justify a GPU ceiling trial. If the bottleneck is uncertain, **HOLD** is safer than a random adjustment.
4. **Change one thing at a time.** Capture the baseline, verify the current rendering point, make one supported actuator change and wait for clean new samples. During GPU Clock/VRS validation, Governor TDP probes and overlapping resource experiments are paused.
5. **Accept or roll back.** Compare *new* Real/Output FPS, real-frame p95, power draw and thermal conditions against the baseline. A rejected trial restores the previous policy; an unconfirmed restore blocks further experiments.
6. **Learn and revisit.** After healthy play, test whether an operating point can become more efficient or whether a previously lowered FPS goal can be raised again. Repeated bad watt floors are remembered and progressively backed off, even across plugin restarts.

### A typical example

Imagine a Steam Deck OLED set to 90 Hz. The game consistently renders **30 real FPS**, while generation produces approximately **90 output FPS** at **×3**. Autopilot does not automatically increase TDP just because the GPU is 99% busy. If that operating point is confirmed and useful, it can keep the current settings and consider an efficiency check later.

In a tougher scene, real-frame delivery begins to fall. Governor can alter its generation operating point or power limit. **Auto keeps a 90 Hz display goal rather than implicitly dropping it to 45 FPS on low Real FPS.** The explicitly selected **Battery** preference may deliberately choose a **45 output FPS** goal and later retry 90. A 60 FPS goal is used only on the Deck LCD and on an external display. Deep emergency ratios above ×3 are temporary: Governor periodically attempts to restore the normal real-frame cadence, with rollback when unsuccessful. Display cadence still needs device testing.

If the GPU appears shader-limited, Autopilot can consider Half Rate Shading, when **Try Half Rate Shading** is enabled. When evidence does not identify a helpful action, it waits.

*These figures demonstrate decision-making, not measured battery, latency or FPS improvements.*

### Three preferences

The mode's Home screen offers:

- **Auto:** balance consistency and efficiency; hold a good configuration when evidence does not justify an intervention.
- **Battery:** give more weight to lowering power and allow an achievable lower output target under sustained constraints.
- **Smoothness:** prioritize a consistent real-frame cadence, using Governor's smoother operating-point preference and fewer speculative changes.

The separate **Try Half Rate Shading** toggle permits VRS experiments for the active game profile only. It is on by default; an explicit saved off choice is preserved. Enabling it does not guarantee that the feature will actually activate.

### Deliberate pauses, restoration and limitations

GPU Clock and VRS trials cannot begin while Steam's Quick Access Menu (QAM) is open, during scene transitions, without a confirmed renderer point, on stale or insufficient telemetry, at critical temperature, on an unsupported system or while an earlier change awaits rollback. Steam's manual settings take precedence over GFG-owned changes.

On **Stop**, game exit or a mode change, GFG attempts to restore only the controls it owns. **HOLD**, **PAUSE**, **Testing**, **Rollback** and **Restore pending** mean different things. A *proposed* optimization is not evidence that a write was applied.

**Hardware caveat:** mock backend tests pass, but real-device operation of dynamic GPU Clock and Half Rate Shading has not been validated on Steam Deck LCD/OLED. **Allow Tearing is not automatically controlled.** VRS 2×2 changes game shading generally, **not only generated intermediate frames**, and can blur text and fine details.

<div align="center">
<img src="docs/img/card-autopilot.png" alt="Autopilot's confirmed configuration and skipped trial states" width="800">
<sub>Actual 2.1.2 Autopilot cards using illustrative measurements: a verified operating point and a deferred experiment with no hardware write.</sub>
</div>


## Modes

<div align="center"><img src="docs/img/card-modes.png" alt="Battery, Balanced, Quality, Autopilot" width="900"></div>

| Mode | Priority | How it works |
| --- | --- | --- |
| **Battery** | Efficiency | Searches lower TDP first; ratios up to ×3; ×3.25–×3.75 only when needed |
| **Balanced** | Consistency | Starts near 12 W; ratios up to ×3; ×3.25–×3.75 only when needed to preserve output |
| **Quality** | Real-frame quality | Prefers fewer generated frames, considers quarter steps through ×3.75, then looks for watt savings |
| **Autopilot** | Whole-system orchestration | Coordinates output targets, frame generation, power, GPU Clock, compatible rendering trials and independent CPU/Flow modules |

Performance depends on the game, scene, rendering backend, refresh rate and power limits. These are strategies, not guaranteed frame-rate floors.

## In-game overlay

<div align="center">
<img src="docs/img/hud-rings-standard.png" alt="Autopilot HUD rings for real and output FPS, power and host telemetry" width="900">
<sub>The actual GFG HUD bitmap on an illustrative background; sample measurements, not a capture of game performance.</sub>
</div>

The optional Vulkan rings overlay shows output and real FPS, TDP, and additional Autopilot metrics where available. Missing or stale readings are shown as unavailable rather than green. Configure style, detail and position in **Settings → In-game overlay**. In cases where the rings cannot load, GFG uses a text-line fallback.

## Other features

GFG Extreme 2.1.5 includes the earlier Governor work, alongside the Autopilot:

- **Per-game profiles**, remembered viable operating points and explicit reset of learned game data.
- **Smart CPU/GPU power split**, which can trial a CPU cap in a GPU-bound game and restore it if measured performance worsens. Available only where the OS permits safe control.
- **Frame OS** offers Observe, Shadow and Act; Autopilot defaults to Act. The Act path has not been proven to improve each game; it can yield or roll back when unstable.
- **vkBasalt filters** for sharpening, anti-aliasing and color looks; game restarts may be required for initial layer loading.
- **Session summaries and Diagnostics**, including recent FPS/frametime/power estimates, reasons for Governor decisions and exportable logs.
- **GFG Shell 0.4** (optional): a controller-first Gaming Mode front-end built with Godot, installed and launched from the plugin. Steam stays the game client. It shows the whole Steam library, including owned games that are not installed, and has Quick settings with GFG rings and switches. See [docs/GFG_SHELL.md](docs/GFG_SHELL.md).

<div align="center">
<img src="docs/img/card-power-split.png" alt="CPU/GPU power split details" width="390">
<img src="docs/img/card-frame-os.png" alt="Frame OS information" width="740">
<img src="docs/img/card-filters.png" alt="Shader filters" width="740">
</div>

## Installation

Requires [Decky Loader](https://decky.xyz/) and [Lossless Scaling on Steam](https://store.steampowered.com/app/993090/Lossless_Scaling/) for the supported GFG generation setup.

1. Download [**GFG-Extreme-v2_1_5.zip**](https://github.com/wavessevaw/GFG-Extreme/releases/download/v2.1.5/GFG-Extreme-v2_1_5.zip). Use Decky's **Install from zip** feature and approve the requested permissions for supported power controls.
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

**Software release: 2.1.5.** Version 2.1.4 preserved the 90 FPS Auto goal and single-owner hardware TDP budget. Version 2.1.5 adds bounded real-frame quality recovery from the ×4 emergency ratio, with regression tests. Automated software validation does not establish improved frame rate or latency on a physical Steam Deck. This **does not** imply Steam Deck LCD/OLED hardware validation of dynamic GPU Clock or Half Rate Shading. Generated-frame acquisition timeouts and Frame OS Act gains need independent device testing. Allow Tearing is not automatically controlled.

Measured output cadence is not the same as optical frame delivery. The 60/90 target transition on OLED, visual quality with VRS and physical restore behavior must be checked in games before performance or battery claims.

[Official release notes](RELEASE_DESCRIPTION_V2_1_5.md) · [Known limitations](docs/GFG_GOVERNOR_KNOWN_LIMITATIONS.md) · [Autopilot acceptance](docs/AUTOPILOT_ACCEPTANCE.md)

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

## Frame Fusion and short Boost

Stable 2.1.5 includes both [Fusion Core and Native Fusion](docs/FRAME_FUSION.md), plus [short Boost and right-stick touch](docs/STICK_TOUCH_BOOST.md). **Fusion and Boost run only in Autopilot.** Their switches, frame timing, Stall Shield and compatible shading trials default on; explicit saved off choices remain off. The normal Battery, Balanced and Quality paths do not execute Fusion or Boost.

Fusion can avoid a compatible scaler-input transfer or the native BGRA conversion. Steam Deck field logs confirm the native path executes; they do not establish an overall FPS, energy or input-latency gain. Incompatible formats and resource failures retain the existing path. Leaving Autopilot closes the shortcuts immediately; private history replacement follows the renderer's bounded transition.

With Continuous Boost off, Short Boost requests a **500 ms pulse on right-stick touch**; camera/action input and contact with motion can request up to **1.5 seconds**, then return to calm. Continuous input cannot turn it into a permanent power increase. A recovery gap, energy bank, compatible executor, temperature/output guards and fresh short cadence observations remain in force. A request or policy acknowledgment is not delivered FPS.

**Continuous Boost** is an optional Autopilot switch, off by default. It holds the higher real-frame cadence without the 1.5-second pulse limit and can use more power. Menus, heat, ineffective delivery and power-search guards still pause it.

The built-in profile is shown as **stable** in Profiles. Its existing persisted identifier is retained so saved profiles and Steam launch commands continue to work. Users of the 2.1.2 test builds (Temporal Engine, GFG Shell, Native FG) should install the stable 2.1.5 ZIP explicitly.

<div align="center"><img src="docs/img/card-profile.png" alt="Profiles with the built-in stable profile" width="390"></div>
