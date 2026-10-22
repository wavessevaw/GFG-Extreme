# GFG Extreme 3.0.9

Lower plugin cost: a lighter engine (GSF Kedavra 1.3.0), a working Power Split, filters that step
back in GPU-starved games, and a Governor that finds a stable point and keeps it.

> Tested in CI, in the sandbox and in 39 stress runs. **Not yet checked on a Steam Deck.**
> Engine numbers below are software (lavapipe) measurements, not Deck measurements.

## Engine: GSF Kedavra 1.3.0
- **Motion select and repair run once per frame pair**, not for every generated frame. A generated
  frame now only projects and warps (software bench: 56 -> 5.4 ms per generated frame; whole pair
  x3 -23 %, x3.75 -35 %).
- **Filters (vibrance, sharpening, AA, HDR look) run once per game frame**, not once per shown frame.
- Motion search exits early on still areas; warp skips a side with zero weight.
- New status field `gpu_analysis_us_avg`: the GPU time of a pair's analysis, which was never counted
  before. Reports now carry it.

## Governor
- **TDP goes down boldly, up reluctantly and with checks** (Autopilot, Battery). A raise needs two
  failed windows in a row and goes up by 1 W; a step down goes 2 W.
- **80-83 fps of 90 is fine.** Output down to 88 % of the cap does not raise the TDP. A step down is
  only tried when output holds 95 % of the cap, and a step that dips is reverted.
- **Stable Point.** After six steady windows the found TDP is locked and guarded. It is remembered
  per game and refresh rate; next launch Autopilot starts from it instead of measuring at full
  power. The lock is released on a failed window, a much lighter scene, or a mode change.
- **The Steam TDP slider is a ceiling.** The Governor never goes above the player's value.

## Power Split
- **Fixed: the CPU cap was never applied on a Deck.** The kernel shows the new CPU limit a moment
  after the write, so every attempt was rejected. The plugin now waits for it (up to 0.5 s).

## Filters in GPU-starved games
- When the GPU is busy above 90 % for 20 s and the point is low, filters get lighter first (AA,
  HDR look and clarity off, DLS -> CAS), then off. They come back after 90 s of headroom. Quality
  mode never sheds filters.

## HUD
- The in-game HUD is drawn from cached tiles: about 0.5 ms instead of 10.7 ms of CPU per update,
  pixel for pixel the same picture.
