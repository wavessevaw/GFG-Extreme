# GFG Extreme 2.0.1-alpha.1

Release status: pre-release

Supersedes the 2.0.0 pre-release. Not merged to main. Not the stable release.

## Fixes
- The FPS goal Autopilot chooses is the goal Governor and BudgetController use. It is not only a planner label.
- The FRAME ring judges real-frame time against the confirmed multiplier. Stable 45×2 and 30×3 stay green.
- Stop, a disabled Governor and a new game clear the Autopilot HUD session. The ordinary rings come back.
- A GPU-clock check, still read-only on device, is judged only from samples taken after the change.
- PAUSE and HOLD block planned probes. Protective budget reactions stay available.

## Not claimed
No FPS gain or watt saving is claimed. GPU clock writes stay off until a Steam Deck proves restore.

## Log
Stop a recording to export the usual ZIP.
