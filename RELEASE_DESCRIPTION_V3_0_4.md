# GFG Extreme 3.0.4

Autopilot becomes its own adaptive mode.

> Tested in CI and in the sandbox. **Not yet checked on a Steam Deck.**
> Coming from 3.0.1 or older: Setup → Reinstall engine, then reboot (HDR fix from 3.0.2).

## Autopilot

- Autopilot no longer switches between Battery, Balanced and Quality. It is one mode that keeps
  adapting to the game: the pilot picks the base frame rate, the Governor the TDP.
- **Starts at 15 W** and measures the game there.
- **Tolerates dips of 8–10 %** in the game's frame rate: no extra watts for those. A deeper fall
  gets watts back at once (full power when the game collapses).
- **Power target 12 W, ideal 9–10 W.** The Governor may go higher to hold a point, but a point that
  needs more than 12 W for a minute is given up for the next lower one (not retried for 10
  minutes), and Autopilot climbs only while the TDP is at 10 W or less.
- **x3.75** only below 20 % battery (back above 25 %), with the "battery" preference, or when a
  game cannot hold x3 even at full power.
- Heat no longer changes the mode: above 90 °C the Governor lowers the limit itself.

Everything from 3.0.3 (Governor 2.0 groundwork, centred HUD numbers) is included.
