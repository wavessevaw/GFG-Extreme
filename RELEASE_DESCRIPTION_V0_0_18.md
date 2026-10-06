## GFG Extreme Decky: Governor v0.0.18 (pre-release)

**Review follow-up to v0.0.17.**

> **Pre-release.** Please keep sending logs (Settings → Diagnostics → Record a log).

### Fixed
- **A stale overlay change can no longer reach MangoHud after the overlay is turned off.** v0.0.17 coalesced rapid overlay changes into a pending config; turning the overlay off before the 5 s interval ended could still publish that older config once. Now the desired state is decided first and applied once, a newer state replaces an older pending one, and turning the overlay off drops anything pending.
- **A point inferred from delivered FPS is a candidate, not a verified point.** When a request times out but the target was delivered at fewer real frames, the Governor moves to the matching point and marks it as *verifying*: the renderer has to confirm it on fresh samples, and two fresh windows (real-frame p5, output, delivery misses, hard pressure, frame pacing) must hold before it counts as held. Until then it is not remembered for the next session, and a bad window escalates as usual. Details shows the state in the log as `verifying`.

Everything from v0.0.17 is included.

### Install
1. Download `GFG-Extreme-Governor-v0_0_18.zip` and install it through Decky Loader (install from zip). Accept the root access request.
2. Close the game, press **RUN**, start the game.

### Verify your download
SHA-256 of the zip: `<sha256>` (see `SHA256SUMS.txt`).

### Known limitations
See `docs/GFG_GOVERNOR_KNOWN_LIMITATIONS.md` (items 24–25).
