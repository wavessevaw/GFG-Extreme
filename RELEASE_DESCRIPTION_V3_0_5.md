# GFG Extreme 3.0.5

Autopilot ignores short frame-rate drops and aims for a base frame rate above 30.

> Tested in CI and in the sandbox. **Not yet checked on a Steam Deck.**

## Autopilot

- **A short sharp drop is no reason for watts.** The Governor raises the TDP only when the game
  stays short for 5 of the last 6 seconds; its windows and the pilot's guard look at the median
  frame rate, so one bad second does not count.
- **Aim: base above 30 (multiplier below x3); x3 is good; x3.75 is the last resort.** Autopilot
  climbs to the first point above 30 while the TDP is within the 12 W target, and higher ones
  from the 9–10 W ideal. The power target never pushes the point below 30.

Everything from 3.0.4 (Autopilot as one adaptive mode, start at 15 W, 8–10 % dips tolerated)
is included.
