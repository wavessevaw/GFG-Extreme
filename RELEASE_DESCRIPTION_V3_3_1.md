# GFG Extreme 3.3.1

Camera turns without jelly or blocks, steadier Autopilot and calmer power management.
**Update engine** and reboot after installing.

## New engine: GSF Kedavra 1.4.3
- **The world turns as one image.** The camera's motion is now fitted as a plane projective map,
  the exact image motion of a turning camera, where the sides move faster than the centre and
  along curves. Wherever the picture agrees, a pixel follows that map instead of its 4×4 block,
  so the jelly of a turn and the square blocks at the sides of the screen are gone.
- **The true phase of a turn.** Each generated frame shows the camera turned by exactly its share
  of the angle, so generated frames no longer wobble at the sides during a fast turn.
- **Same cost.** Analysis and synthesis cost the same as before within a few percent.

Engine test (1280×800), 3.3.0 → 3.3.1:

| Scene | Generated frames | Frame-to-frame error (lower is steadier) |
|---|---|---|
| Camera turn, up to 10° per frame | 25.35 → 27.56 dB (screen sides 23.68 → 26.62 dB) | 8.70 → 5.18 |
| Climbing stone steps | 25.43 → 30.93 dB | 3.25 → 2.20 |
| Walking forward up stairs | 21.84 → 24.55 dB | |

## Steadier Autopilot
- **A point is kept once it is chosen.** When the game does not hold the next point up, that
  point waits 1, 2, 4, 8 and up to 16 minutes before the next try, so the multiplier no longer
  switches back and forth every minute in a game that sits near its limit.
- **Short trials.** A try that is clearly short ends after 4 seconds instead of running to the end.

## Calmer power management
- After raising the power limit the Governor waits before probing down again (30 s, longer each
  time a probe does not hold), and steps down in 1 W steps near a level that did not hold.

Plugin sandbox, a game near its limit with a new scene every 15–45 s, one hour, 3 seeds,
3.3.0 → 3.3.1:

| Mode | Multiplier changes per hour | Time at the target FPS |
|---|---|---|
| Autopilot | 14.7 → 13.0 | 83.2 → 87.6 % |
| Balanced | 25.7 → 13.0 | 90.6 → 91.6 % |

Power limit changes per hour under Autopilot: 84 → 48. Two-hour session with slow load waves
(Balanced): power limit changes 120 → 76, time at the target FPS 97.6 → 98.4 %.

## Benchmark
- Nothing changes in game while the Benchmark waits for the Quick Access menu to close; the
  measurement and its centred panel start once you are back in the game.
