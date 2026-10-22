# GFG Extreme 3.0.10

Mode rules from the user: one 15 W ceiling, a lowest multiplier per mode, and "down boldly, up
slowly" in every mode. Same engine as 3.0.9 (GSF Kedavra 1.3.0).

> Tested in CI, in the sandbox and in 39 stress runs. **Not yet checked on a Steam Deck.**

## Modes
- **Never above 15 W in any mode.** Quality, Balanced and Battery now share Autopilot's ceiling,
  even when SteamOS's own TDP is 20 W.
- **Balanced works down to x3** (30 fps base at 90 Hz). It no longer drops to x3.75.
- **Quality works down to x2.5** (40 fps base at 90 Hz, x2.25; 35 would be x2.6).
- A game too heavy for the mode's lowest point stays on it and the panel says the point does not
  hold. Battery or Autopilot can go lower (x3.75).

## Governor
- **TDP goes down boldly and up slowly in every mode**, Balanced and Quality included: a raise
  needs two failed windows in a row and goes up 1 W; a severe drop gets 2 W at once, not the whole
  ceiling. In a long varying session this costs a little smoothness in Balanced (sandbox: 96.8 %
  of seconds at the point, before 97 %+).
