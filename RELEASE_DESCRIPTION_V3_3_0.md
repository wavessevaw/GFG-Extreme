# GFG Extreme 3.3.0

Lower latency, steadier motion at every multiplier, a one-button Benchmark and a system profile
tuned for games. **Update engine** and reboot after installing.

## New engine: GSF Kedavra 1.4.2
- **Lower latency.** Motion analysis now runs in a single refresh, so every generated frame is
  ready one refresh sooner.
- **Steady speed at every multiplier**, including fractional ones like ×2.25: fractional bases
  run on their real rhythm (40 FPS at 90 Hz releases 2-2-2-3).
- **No jump after a stall**: long gaps are filled frame by frame.

Scheduler simulation, 3.2.1 → 3.3.0:

| Case | Speed changes | Latency |
|---|---|---|
| ×2, base 45 | 0 → 0 % | 33.3 → 22.2 ms |
| ×2.25, base 40 | 77.8 → 0 % | 37.8 → 33.3 ms |
| ×2.6, base 35 | 0 → 0 % | 44.4 → 33.3 ms |
| ×3, base 30 | 0 → 0 % | 44.4 → 33.3 ms |
| 60 Hz ×2, base 30 | 0 → 0 % | 50.0 → 33.3 ms |
| 60 Hz ×2.4, base 25 | 83.3 → 0 % | 60.4 → 50.0 ms |

## Multiplier follows the game
- Above 30 FPS Autopilot uses the fractional ×2 family (35 / 40 / 45 at 90 Hz) for more real
  frames and lower latency; ×3 is kept for games that stay at 30.
- On a low battery Autopilot keeps the ×2 family within 12 W.

## Benchmark
- **Dash → Benchmark**: 20 seconds in game, with a centred *Do not touch anything* panel. GFG
  measures the game's own FPS, GPU and CPU load, power and temperature and proposes a strategy:
  base FPS, multiplier and expected watts.
- **Accept** saves it for the game: every next launch starts right there, and Autopilot uses it
  as its compass while it keeps adapting to each scene.

## System profile for games
- Installed together with the engine, in one step: memory tuned for games (transparent huge
  pages, early reclaim, zram-tuned swap), a CPU scheduler without autogroup, and storage
  schedulers tuned for asset streaming on NVMe and microSD.
- **Remove** in Setup takes it off together with the engine.

## Smoother frame pacing
- GFG no longer changes the CPU and GPU clocks during play by default: the Governor manages
  power through the TDP alone, for a steadier picture. Power Split and the GPU clock ceiling
  remain available on the Engine tab.
