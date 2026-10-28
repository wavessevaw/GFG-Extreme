# GFG Extreme 3.3.0

New engine GSF Kedavra 1.4.2 with lower latency and steady speed at every multiplier, a
Benchmark on Dash, a system profile for games installed together with the engine, and Power
Split and the GPU clock ceiling off by default. **Update engine** and reboot after installing.

## Engine: GSF Kedavra 1.4.2
- The motion analysis runs in one refresh when it fits (under a third of the refresh period), so
  a generated frame is ready one refresh sooner.
- A slow-down is no longer paid back with a speed-up, and fractional caps follow their real
  rhythm (40 FPS at 90 Hz releases 2-2-2-3). No forward jump after a stall.

Simulator, stable base (1.4.1 → 1.4.2):

| Case | Outputs at a changed speed | Latency |
|---|---|---|
| ×2, base 45 | 0 → 0 % | 33.3 → 22.2 ms |
| ×2.25, base 40 | 77.8 → 0 % | 37.8 → 33.3 ms |
| ×2.6, base 35 | 0 → 0 % | 44.4 → 33.3 ms |
| ×3, base 30 | 0 → 0 % | 44.4 → 33.3 ms |
| 60 Hz ×2, base 30 | 0 → 0 % | 50.0 → 33.3 ms |
| 60 Hz ×2.4, base 25 | 83.3 → 0 % | 60.4 → 50.0 ms |

Simulator, game near its cap (1.4.1 → 1.4.2):

| Case | Outputs at a changed speed | Latency | Jumps per minute |
|---|---|---|---|
| ×2, base 45 | 43.6 → 1.6 % | 40.9 → 36.0 ms | 8.9 → 0 |
| ×3, base 30 | 25.1 → 1.1 % | 49.9 → 46.1 ms | 0.4 → 0 |
| 60 Hz ×2, base 30 | 42.8 → 1.4 % | 56.1 → 54.2 ms | 0 → 0 |

## Multiplier follows the game
- Above 30 FPS Autopilot aims for the fractional ×2 family (35 / 40 / 45 at 90 Hz). ×3 only
  when the game does not get above 30.
- A low battery keeps the ×2 family within 12 W instead of locking ×3.

## Benchmark
- **Dash → Benchmark**: 20 s in game at 15 W with generation off, with a centred *Do not touch
  anything* panel. The medians of FPS, GPU and CPU load, power and APU temperature give a
  proposed base FPS, multiplier and watts.
- **Accept** stores it per game: the next launches start there and Autopilot uses it as its
  compass while still adapting to the scene. **No, keep searching** keeps the normal search.
  The Steam menu, a pause or a game change cancels the run.

## System profile
- Installed with the engine, in the same step and boot unit; **Remove** writes every saved
  value back. Runtime kernel settings only: no change to the read-only image, kernel command
  line, drivers, packages or security mitigations.
- Memory (transparent huge pages, earlier reclaim with a larger reserve, no proactive
  compaction, zram-tuned swap, MGLRU thrash protection), CPU (no autogroup, no lockup
  watchdogs) and storage (kyber on NVMe, BFQ on microSD, 1 MiB read-ahead).

## Power Split and GPU clock ceiling off by default
- Each CPU cap change made short pacing dips more frequent (2.6 → 4.0 % of the following
  seconds, about one change a minute) for a median gain of 0.6 % GPU clock per watt (plugin
  telemetry, 7 h of play). Both stay available as switches on the Engine tab.

## How to check
Play a few minutes, then **Setup → Save report to Desktop** and send the report.
