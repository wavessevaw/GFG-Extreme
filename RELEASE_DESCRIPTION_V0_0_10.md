## GFG Extreme Decky: Governor v0.0.10 (pre-release)

**A simpler interface, a Governor that can see the machine, and a safer release pipeline.**

> **Pre-release, not yet tested on a Steam Deck.** Please record a log (Settings → Diagnostics → Record a log) in a game with the Governor on, and send it.

### Interface (from the UI audit)
- **Home is one screen of decisions:** the target ring, Real → GFG → Output, the Run button, the **Battery / Quality** switch, and two entries: **Details** and **Settings**.
- **Contextual help instead of permanent buttons.** The launch command appears on Home only while the game is not attached to GFG. "Something wrong? Record a log" appears only when the Governor is paused or cannot reach the target.
- **Settings** gathers overlay, profile, launch command, frame generation backend and scaling. **Support** holds Diagnostics (record a log, journal), System and All settings.
- **Backend errors are visible.** A failing call shows a banner instead of being swallowed.

### The Governor can see now
- New read-only sensors: **temperature and its trend, GPU busy and clock, busiest CPU core, fan, battery draw**.
- **Frametime statistics** of the real cadence: median, p95, p99, jitter, stutter ratio. Two points with the same average FPS no longer look the same.
- **A one-line verdict** shown on Home and in Details: GPU-bound / CPU-bound / TDP-limited, thermal state, smooth or stuttering.
- **First decision that uses it:** a CPU-bound game never gets render-scale points (they cost picture quality and give no real frames).
- Everything is in the recorded log (`timeline.jsonl`).

### Reliability
- New **CI** runs the backend tests, rebuilds the frontend, checks that `dist/index.js` is current and runs the 25-screen frontend smoke test on every push and pull request. The release workflow runs the same checks.
- The frontend test no longer depends on a machine-specific tool path (`npm ci` is enough).

Everything from v0.0.9 is included.

### Install
1. Download `GFG-Extreme-Governor-v0_0_10.zip` and install it through Decky Loader (install from zip). Accept the root access request.
2. Close the game, press **RUN**, start the game.

### Verify your download
SHA-256 of the zip: `<sha256>` (see `SHA256SUMS.txt`).

### Known limitations
See `docs/GFG_GOVERNOR_KNOWN_LIMITATIONS.md` (items 19–20). The sensors are read from sysfs and have not been checked on a Deck.
