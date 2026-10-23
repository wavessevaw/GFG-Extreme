# GFG Extreme 3.2.1

New engine GSF Kedavra 1.4.1: even smoother frame delivery and cleaner screen edges. Same latency,
no extra GPU passes. No new settings and no UI changes. **Update engine** and reboot after
installing.

> Tested in CI. The numbers below come from the engine's scheduler simulator and from lavapipe (a
> CPU Vulkan driver), not from a Steam Deck. **Not yet checked on a Steam Deck.**

## Smoother pacing
- When the frames that are ready would run out (a late game frame), the picture now slows down to
  as little as a quarter speed for a moment instead of stopping. If the motion analysis finishes
  later than predicted, a half-step that is already ready is shown instead of a freeze.
- The scheduler's look-ahead reads its history once per refresh instead of once per predicted
  refresh.

Hitches per minute in the simulator (a hitch = the picture stops or jumps), 3.2.0 → 3.2.1:

| Case | Hitches per minute | Median latency |
|---|---|---|
| ×2 at 60 Hz (TV), game near its cap | 5.28 → 0.45 | 54.57 → 54.56 ms |
| ×3 at 90 Hz, game near its cap | 11.58 → 7.08 | 45.06 → 45.06 ms |
| ×2 at 90 Hz, game near its cap | 16.07 → 9.10 | 37.36 → 37.36 ms |
| Base 24 at 90 Hz | 16.86 → 12.03 | 51.02 → 51.01 ms |
| ×3 at 90 Hz, game with room | 10.34 → 5.84 | 46.74 → 46.73 ms |

Long game stalls still cannot be hidden: there is no frame to move to.

## Screen edges
- Near the borders of the screen the generated frame now fades to the source frame that really has
  those pixels, instead of stretching the outermost pixels. Panning past the edge looks steadier
  (border PSNR +0.75 dB on a pan, lavapipe at 1280×800).
- A few redundant texture reads in the warp are skipped. The sharpness filter and the motion
  analysis resolution are unchanged.

## How to check
Play a few minutes, then **Setup → Save report to Desktop** and send the report.
