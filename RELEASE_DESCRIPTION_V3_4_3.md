# GFG Extreme 3.4.3 — Quick Benchmark fix

## Fixed

- **15-second measurement budget.** The HUD Benchmark now uses a short descending TDP scan instead of spending two long windows plus 3 seconds of settling at every wattage.
- **No more oscillating back to maximum TDP.** Scan steps descend by 2 W. Only a single return to the proposed point is permitted for confirmation.
- **Verified recommendation.** Two fresh native-frame samples at the selected power are required before a measured point can be applied. The original FG policy and display counters are checked afterward, within the same time budget.
- **Clearer endings.** A transient stale Gamescope report does not cancel a run. Genuine menu, game, power-control and thermal changes still cancel safely. If enough evidence is not available before the deadline, the result is marked *Not confirmed* and cannot be applied.
- **Mode-aware behavior retained.** Quality prioritizes native FPS, Balanced targets a compromise, Battery targets 30 native FPS at 60/90 Hz, and Autopilot uses its supported FPS ladder.

## Scope and compatibility

Only the Benchmark and its HUD reporting have been changed. Governor, frame interpolation, optical flow, Focus, and Silk scheduling algorithms are not modified. **GSF Kedavra remains version 1.6.2**, with the same bundled Gamescope runtime as GFG 3.4.2. No standalone GSF installer is included in this GFG release.

## Installation

Install `GFG-Extreme-v3_4_3.zip` with Decky Loader. If you already have the matching Kedavra 1.6.2 runtime from GFG 3.4.2, there is no engine change to install. Follow Setup's prompts if its engine check reports a mismatch. Benchmark is started and confirmed exclusively from the game HUD, not Dash.

## Validation

Automated tests cover mode selection, scan duration, no repeated ceiling probes, TDP write ownership, missing telemetry, result confirmation, restoration, virtual Deck scenarios and UI smoke testing. **Physical Steam Deck FPS, touch, APU power and P95/P99 testing has not been performed by CI.** A 15-second ceiling prevents prolonged automatic measurements; insufficient data will produce no validated optimization rather than a fabricated result.
