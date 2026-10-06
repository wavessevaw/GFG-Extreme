## GFG Extreme Decky: Governor v0.0.15 (pre-release)

**"Check setup": find out why something does not work, without recording a log.**

> **Pre-release, not yet tested on a Steam Deck.** Please record a log (Settings → Diagnostics → Record a log) in a game with the Governor on, and send it.

### New
- **Settings → Diagnostics → Check setup** runs every precondition of the Governor and the in-game overlay in a second: launcher installed and up to date, engine files present, the MangoHud Vulkan layer on the system, overlay switched on and its config published, renderer diagnostics log present and writable, TDP access, profile and Desktop folder. Failed checks come first, each with **what to do about it** and the path or detail it checked; passing checks are listed below. **Check again** re-runs it.
- The same checks are in every recorded log (`self_test.json`) and feed the verdict in `summary.txt`.

Everything from v0.0.14 is included.

### Install
1. Download `GFG-Extreme-Governor-v0_0_15.zip` and install it through Decky Loader (install from zip). Accept the root access request.
2. Close the game, press **RUN**, start the game.

### Verify your download
SHA-256 of the zip: `<sha256>` (see `SHA256SUMS.txt`).

### Known limitations
See `docs/GFG_GOVERNOR_KNOWN_LIMITATIONS.md`. The checks verify that the files and permissions the overlay and the Governor need are in place; they cannot prove that MangoHud draws the bar inside a particular game.
