## GFG Extreme Decky: Governor v0.0.6 (pre-release)

**Battery first.** The Governor now looks for the lowest TDP that holds the target and only then spends spare headroom on fewer generated frames. Example: instead of 45x2 at 18 W it aims for 30x3 at 9–11 W.

> **Pre-release, not yet tested on a Steam Deck.** Please record a log (Home → Record log) and send it.

### New: Battery mode (default)
- **TDP budget.** 9–11 W is the target. 12–15 W is for heavy games. 16–20 W is used only as a last resort, while real FPS stays below about 22 for a minute.
- **Multipliers ×1 to ×3.75** in 0.25 steps (real FPS never below 24). **×4** only as a last resort.
- **How it searches.** It starts at 30 real FPS (30x3 at 90 Hz, 30x2 at 60 Hz) and 10 W, then lowers TDP 1 W at a time. A failed level returns to the last good one. After that it tries fewer generated frames at the same watts.
- **When a scene gets heavier** the order is: more generated frames (down to 30 real), then up to 11 W, then ×3.25–×3.75, then up to 15 W, then ×4, and 16–20 W last.
- **When a scene gets lighter** it tries −1 W again after 5 minutes of clean play, backing off after a miss. Quality given up to a heavy scene is won back.
- **Quality mode** (the previous behaviour) stays available: Governor → Mode.

### Fixed (from the algorithm review)
- **Guard after LOCKED.** Previously nothing reacted to a heavier scene after the Governor locked. Now two bad windows (one if FPS drops hard) trigger the guard.
- **No locking after a single window.** A TDP level or point needs two clean 15 s windows in a row.
- **One definition of "holds"** everywhere: real p5 ≥ 95 % of the cap, output ≥ 94 % of the target, no hard pressure, at most one miss per window. Frame pacing (p95 frame interval from the renderer) now counts, so a stutter hidden by averages fails the window.
- **TDP changed outside GFG** no longer pauses forever: in Battery mode GFG takes it back after 30 s, at most 3 times.
- Overlay multiplier now comes from the FPS medians, matching the FPS shown (#20).

### Install
1. Download `GFG-Extreme-Governor-v0_0_6.zip` and install it through Decky Loader (install from zip). Accept the root access request.
2. Close the game, press **RUN**, start the game.

### Verify your download
SHA-256 of the zip: `<sha256>` (see `SHA256SUMS.txt`).

### Known limitations
See `docs/GFG_GOVERNOR_KNOWN_LIMITATIONS.md`. The watts saved per step are not measured yet (only the PPT limit is known); the thresholds are design choices that need Steam Deck logs to tune. Fractional points above ×3 rely on the renderer's adaptive mode with a ×4 ceiling, which is not yet verified on hardware.
