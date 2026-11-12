## What's New in 3.4.4

- **Apply works:** A measured Benchmark point can now be applied to the current game and performance mode, including provisional results.
- **No more immediate TDP rebound:** Applying 12 W starts Governor at 12 W instead of restoring 16 W and re-running a maximum-power probe. Power can still rise when the game demonstrably needs it.
- **Clear result actions:** APPLY / DISCARD for a measured point; RETRY / DISCARD when no valid point was measured.
- **Per-mode memory:** The chosen TDP and native FPS target are saved independently for Quality, Balanced, Battery and Autopilot. Existing accepted Benchmark results remain compatible.
- **Engine unchanged:** GSF Kedavra 1.6.2, Focus and frame-generation algorithms are unchanged.
