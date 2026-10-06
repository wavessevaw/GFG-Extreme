## GFG Extreme Decky: Governor v0.0.17 (pre-release)

**Fixes from the first log recorded on a real Steam Deck** (Witcher 3, Steam Deck OLED, 12 minutes). Thank you for sending it.

> **Pre-release.** Please keep sending logs (Settings → Diagnostics → Record a log).

### What the log showed
- **Battery mode worked:** 90 FPS on screen at 30 real frames (×3) and 10–11 W.
- **Balanced got stuck at 15 W and about 80 FPS.** It asked for 40 real ×2.25; at 13 W the GPU could not render 40 frames, and the renderer delivered the full 90 FPS at 30 real (×3) on its own. The Governor waited for ×2.25, timed out, rejected the point, and then its guard would only try the *neighbouring* deeper point, which was the rejected one. So it bought watts up to Balanced's ceiling and gave up, while ×3 at 10 W was available.
- **The game exited seconds after six overlay changes in eight seconds.**
- MangoHud **was loaded in the game** with GFG's config, so the overlay path itself works.

### Fixed
- **The guard skips rejected points** and goes to the next deeper one, instead of buying watts.
- **"The renderer delivered a deeper ratio" is no longer a failure.** If a request times out but the target was delivered at fewer real frames, the Governor moves straight to the matching point (here 30×3).
- **Overlay changes are coalesced.** While a game runs, the MangoHud config is rewritten at most once every 5 s and only with the latest state; unchanged content is never rewritten.
- **Check setup** no longer reports the optional `/dev/shm` diagnostics fallback as a failure.
- **Log verdict** now points out when a game exited shortly after a burst of overlay changes.

Everything from v0.0.16 is included.

### Install
1. Download `GFG-Extreme-Governor-v0_0_17.zip` and install it through Decky Loader (install from zip). Accept the root access request.
2. Close the game, press **RUN**, start the game.

### Verify your download
SHA-256 of the zip: `<sha256>` (see `SHA256SUMS.txt`).

### Known limitations
See `docs/GFG_GOVERNOR_KNOWN_LIMITATIONS.md` (items 24–25). That MangoHud's reload caused the crash is a hypothesis; the log has no MangoHud output.
