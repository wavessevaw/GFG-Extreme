# GFG Extreme 3.0.3 Independence

Autopilot with a power target, the controller fixes from the Governor 2.0 review, and a clearer HUD.

> Tested in CI and in the sandbox. **Not yet checked on a Steam Deck.**
> Coming from 3.0.1 or older: Setup → Reinstall engine, then reboot (HDR fix from 3.0.2).

## Autopilot: power target

- Good target **12 W**, ideal **9–10 W**. The Governor may still go higher to hold a point, but
  a point that needs more than 12 W for a minute is given up for the next lower one and not
  retried for 10 minutes. Autopilot climbs to a higher point only while the TDP is at 10 W or less.
- Under Autopilot the Governor starts at 10 W.
- Autopilot no longer picks x3.75 (base 24) for battery saving unless the battery is low: x3
  shows far fewer artefacts. A game that cannot hold x3 even at full power still gets x3.75.
  Battery mode chosen by hand keeps x3.75.

## Governor 2.0 groundwork (from the controller review)

- A failed restore of your TDP is retried, and no new game takes over the TDP until it is back.
- While Power Split or the GPU clock ceiling tries a step, the TDP stays fixed; a new window
  starts afterwards.
- A collapse of the game's frame rate brings full power back within 3 readings.
- Auto measures only fresh engine readings, not while the Steam menu is open or during a
  Power Split step.
- Switching HDR or filters restarts the measurement windows (the GPU load changed).
- Session statistics no longer claim "saved Wh" from the difference between limits; they show
  the APU energy actually drawn.

## HUD

- Bold, larger numbers; slightly larger, thinner rings; long values use a smaller bold cut so
  they stay inside the ring, on the same line.
