# GFG Extreme 3.0.1 Independence

The first update after 3.0.0, built from the feedback of the first Steam Deck sessions: a faster,
smarter Governor in the style of 2.1.6, Auto that follows the game's real frame rate, a tidier HUD
and visible gamepad focus.

> Tested in CI and in the sandbox (virtual Steam Deck runs, 29 scenarios).
> **No Steam Deck measurement of 3.0.1 exists yet.** HDR together with frame generation is not
> fixed in this build: it comes in the next one.

## Governor (TDP)

- Starts low, like 2.1.6: 10 W in Battery, 12 W in Balanced, or the last level that held for this
  game plus a watt. It no longer walks down from 15 W one watt at a time.
- Fast descent: 2 W steps every 5 s until the first failure, then 1 W; when the APU draws far less
  than the limit, the limit jumps straight down to the draw plus a margin.
- A 1 s guard: if the real frame rate falls while a lower TDP is being tried, the last good TDP is
  back within about 3 s and that level is remembered as a floor.
- Floors expire (5 min, doubling up to 30 min), so one heavy scene does not block savings forever.
- Thermal recovery fixed: after a hot spell the TDP comes back once the APU cools, also while the
  pilot measures and in Quality.
- The Governor's smoothness threshold now matches the pilot's (it was stricter, which kept the TDP
  at the ceiling).
- No TDP step while Power Split or the GPU clock ceiling runs an experiment; windows with too few
  readings give no verdict.

## Auto and Autopilot

- When the locked base frame rate has GPU and CPU headroom, Auto tries the next point after 10 s
  instead of waiting minutes, so 30 → 45 follows the game quickly. A failed try backs off.
- A measurement no longer locks a stale Auto value when readings stop.
- Autopilot no longer flips between Quality and Balanced around 85 °C: hot until 30 s below 80 °C.

## UI and HUD

- Visible gamepad focus on every control in the panel.
- HUD: every number on one line, the HUD is 12 % smaller, even letter spacing.

## Fixes

- The zip now contains the pacing analyser (Save report / pace recording) and the engine benchmark.
- A failed TDP restore no longer makes the next game treat the lowered TDP as yours.
- Full per-second logs (FPS, real FPS, TDP, draw, temperature, CPU/GPU load and clocks, fan,
  battery and time left, CPU and GPU limits).
