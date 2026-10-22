# GFG Extreme 3.2.0 "Silk"

Smoother frame delivery: new engine GSF Kedavra 1.4.0. Same latency, same GPU work and power.
No new settings and no UI changes. **Update engine** and reboot after installing.

> Tested in CI and in the engine's scheduler simulator (16 pacing scenarios, 3 seeds). The
> numbers below are from the simulator, not from a Steam Deck. **Not yet checked on a Steam Deck.**

## Silk pacing
Your last report (GFG 3.1.2) showed where the remaining stutter came from: the game sometimes
misses its cap (1.7 % of flips were repeats), and about every 14 seconds the engine gave latency
back by skipping a whole frame. Both look like a hitch: the picture stops for one refresh or jumps
by two.

- **Catch-up instead of a skip.** The picture now moves in eighths of a refresh. When it is
  behind, it runs 1.25× fast for a few refreshes (1.5× when far behind) instead of jumping a frame.
- **Slow-down instead of a freeze.** The engine looks a few refreshes ahead. When frames would run
  out (a late game frame), the picture slows down evenly and catches up once the frame is there.
- **No extra cost.** Still one generated or copied frame per refresh, as before: no extra GPU work,
  no extra power, and the latency is the same or lower.

Hitches per minute in the simulator (a hitch = the picture stops or jumps). The economy modes
with a low base FPS gain the most:

| Case | Before → 3.2.0 | Median latency |
|---|---|---|
| ×2 at 60 Hz (TV), base 30, game near its cap | 12.0 → 5.3 | 57.1 → 55.5 ms |
| ×3 at 90 Hz, base 30, game near its cap | 22.2 → 12.8 | 50.7 → 49.2 ms |
| ×2 at 90 Hz, base 45, game near its cap | 19.8 → 11.1 | 37.8 → 37.7 ms |
| ×3 at 90 Hz, game spikes | 21.1 → 11.0 | 46.7 → 46.7 ms |
| ×3.75 at 90 Hz (Battery, with Allow above ×3), base 24, game near its cap | 97.7 → 32.6 | 61.6 → 53.2 ms |
| ×3 at 90 Hz, base 30, game with room | 65.9 → 15.0 | 42.6 → 42.6 ms |
| ×2.5 at 60 Hz (TV), base 24, game near its cap | 32.9 → 8.3 | 61.8 → 61.8 ms |

The freezes left are game frames that come far too late: there is nothing to move to. A steadier
base FPS (a lower cap) removes those.

## Also in the engine
- Includes GSF Kedavra 1.3.1: games above 1536×960 (1080p, 4K) are analysed at that size, which
  lightens 1080p on a TV in the dock; on the Deck's own screen nothing changes. VRR stays off while
  frames are generated.
- The engine status has a new `catchup` counter: refreshes where the picture ran slightly faster
  or slower instead of jumping or stopping.

## How to check
Play a few minutes, then **Setup → Save report to Desktop** and send the report. Compare the
repeats and skips with the 3.1.2 report.
