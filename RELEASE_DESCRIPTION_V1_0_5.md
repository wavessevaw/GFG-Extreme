## GFG Extreme 1.0.5

**Fewer dips in Battery mode, a heat check that does not flip back and forth, and your recent sessions.**

### Fixed
- **Repeated FPS dips from lower-power probes.** A Deck log (29 min, recorded with 1.0.0) showed Battery trying 9 W again and again after each heavier scene: 9 W, 8 W and 10 W failed 12 times in total, and each failure was a short dip to 84–88 FPS. A level that just failed with the current point now waits 2 minutes before the next try, then 4, 8 and at most 10 minutes if it keeps failing. The wait ends early when the game clearly needs less power (a lighter scene), and a level that holds is forgotten. On a model of that session the failed probes went from 12 to 4.
- A failed lower-power probe detected by the fast (1 s) check now backs off the same way as one detected by the 15 s window.

### New
- **Recent sessions.** Details lists your last sessions: length, mode, average FPS, watts and hottest temperature. It makes comparing Battery, Balanced and Quality on the same game easy.
- **Stable heat check.** After heat has held quality back, the APU must read *ok* for 90 s before GFG tries fewer generated frames again. Without this, the *heating* verdict could flip back and forth around its threshold.
- **Log summary:** reports lower-power probes that failed repeatedly at the same level, and states which GFG version recorded the log.

Everything from 1.0.4 is included.

### Install
Download `GFG-Extreme-v1_0_5.zip` below and install it through Decky Loader (*Install from zip*) over your current version; settings, profiles and game memory are kept.

### Verify your download
SHA-256 of the zip: `<sha256>` (see `SHA256SUMS.txt`).
