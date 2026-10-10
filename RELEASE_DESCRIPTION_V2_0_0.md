# GFG Extreme 2.0.0-alpha.1

Release status: pre-release

This is the first Autopilot build on Governor 1.6.9. It is not the stable release. It is not merged to main.

## What changed
- The mode control is Battery, Balanced, Quality, Autopilot. Extreme is no longer offered.
- A saved Extreme profile opens as Autopilot. Its other settings stay.
- Autopilot decides. Governor's BudgetController still moves TDP. There is no second power writer.
- One GPU clock ceiling step is attempted only when the CPU looks limiting and the Steam Deck clock files are present. If those files are missing, the clock is reported unavailable and TDP continues.
- A worse result restores the previous GPU policy. Planned TDP changes wait during that check.
- The ring HUD adds GPU, CPU, TEMP and FRAME. It does not add a second FPS or TDP ring. Missing measurements are grey, not green.

## Not claimed
No FPS gain, latency change or watt saving is claimed. GPU clock control and the full restore path are not verified on a Steam Deck yet.

## Log
Stop a recording to export the usual ZIP. Autopilot decisions are in `governor-events.jsonl` and the 1 Hz timeline.
