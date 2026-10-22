# GFG Extreme 3.0.0 (pre-release)

GFG Extreme now runs on its own frame generation engine: **GSF Kedavra**, built into Gamescope.
MAKO, lsfg-vk and Lossless Scaling are gone. One zip, installed from Decky; the plugin installs
and manages the engine itself, no Desktop Mode scripts.

> Pre-release. Everything below is tested in CI and in the sandbox (virtual Steam Deck runs).
> **No Steam Deck measurement of 3.0.0 exists yet**: pacing, power and battery numbers will be
> published only after hardware runs (see docs/DECK_TEST_PROTOCOL_3_0.md).

## Highlights

- **Frame generation ×2, ×3 and up to ×3.75** on GSF Kedavra (Vulkan compute, motion-compensated,
  KMS-timed presentation). Auto, fixed multipliers, or Custom: your own base FPS cap (20–90).
- **HDR**: generation also works in HDR10 (PQ) and scRGB games (switch in Setup).
- **Autopilot** = GSF Auto + GFG Autopilot: measure, lock, guard, adapt. Modes Autopilot,
  Battery (×3.75 sweet spot), Balanced, Quality.
- **Governor** lowers TDP while the locked point holds and gives power back at the first drop.
- **Power Split** (back from 2.x): in GPU-bound games the CPU clock is capped step by step and the
  watts go to the GPU, proven with A/B/A windows.
- **GPU clock ceiling** (back from 2.x): in CPU-bound games the GPU clock is lowered through SteamOS's
  own control, kept only if the frame rate holds and APU draw drops.
- Both run only on a locked point with the Governor settled, one at a time; your own CPU limits
  and manual GPU clock are always restored.
- **Filters after generation**: presets, CAS / DLS sharpening, FXAA / SMAA, 13 effects.
- **New UI**: Dash / Graphics / Engine / Setup, L1/R1 to switch, the wolf ring (tap to resize),
  device chip (Steam Deck OLED / LCD / Dock).
- **New HUD**: FPS, TDP, multiplier, temperature, battery (time left, ring = charge), pacing; four corners.
- Settings from 2.x are migrated (backup kept); MAKO's system changes are undone.

## Not in 3.0.0

Fan control (SteamOS keeps it; the plugin shows RPM), MAKO features (Frame OS, Frame Fusion,
Temporal Engine, vkBasalt scaling).

## Install

Decky Loader → Settings → Developer → Install plugin from ZIP → `GFG-Extreme-v3_0_0.zip`,
then reboot once when the plugin asks (the engine starts with Gamescope).
