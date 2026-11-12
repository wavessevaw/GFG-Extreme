# GFG Extreme 3.4.1

- Focus remains independent of performance modes and GPU budget. Graphics shows
  compositor processing status and processed-frame counts, including HDR bypass.
- Shutdown drains workers, serializes service stop/tick and preserves failed
  restoration journals for retry. System profile restoration checks readback.
- Reuses the established centred Benchmark panel, ring and five telemetry cells.
  Window progress replaces the old fixed countdown; results are accepted in game.
- Benchmark runs entirely through the game HUD: hold it for 0.8 seconds, keep a
  repeatable scene, then Apply or Discard. Tap the active benchmark to cancel.
  Nothing is added to Dash and no Steam or Decky overlay is opened.
- The sweep measures native displayed-frame intervals with generation disabled,
  APU power, CPU/GPU load and temperature at successive 1 W levels. Two windows,
  baseline rechecks and final repeat measurements reject unstable evidence.
  Quality favors native performance, Balanced targets 35–40 FPS at 90 Hz,
  Battery targets 30 FPS at 90/60 Hz, and Autopilot compares supported points.
  Other displays use their refresh rate. Targets are goals, never fabricated results.
- FG and image settings are restored and checked before accepting a result.
  Displayed real/generated counters and SDR Focus processed-frame counters must advance.
  Applied Quality points above half-refresh are retained; Battery uses its measured target.
  Accepted records are scoped to game, mode, refresh, dock and power source.
  They seed existing adaptive controllers and expire after 24 hours; they are not
  permanent TDP locks. Software cannot identify every scene change or game update.
- The compatible Kedavra 1.6.1 runtime adds HUD touch handling and frame telemetry;
  the accepted Focus shader, optical flow, warp and Silk scheduler are unchanged.

## Install and rollback

Install the full GFG ZIP, then **Setup → Reinstall** Gamescope and reboot. If you
keep standalone Kedavra installed, update it to the companion 1.6.1 ZIP as well:
Download Kedavra only from https://github.com/wavessevaw/GSF_Kedavra/releases/tag/v1.6.1;
GFG packages belong to https://github.com/wavessevaw/GFG-Extreme/releases.
The controller lease pauses standalone commands/HUD while GFG owns the engine.
Older standalone 1.6.0 does not support that protocol: GFG pauses control until it is updated or removed. If removing the old standalone restores system Gamescope, reinstall the GFG runtime afterward.

To roll back, restore system Gamescope from Setup, reboot, install the previous
3.4.0 plugin and runtime and reboot again. Keep the checksum files with the ZIPs.

## Validation limits

Backend, deterministic virtual-Deck, frontend and Gamescope build tests are
software checks. No physical Deck LCD/OLED touchscreen, GPU-budget or compositor
P95/P99 validation is claimed by the build environment. Native frame intervals
are observed by the compositor, not internal game-engine render timings.
