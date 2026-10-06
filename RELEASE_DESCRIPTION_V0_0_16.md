## GFG Extreme Decky: Governor v0.0.16 (pre-release)

**When something is wrong, Home says what, and what to do.**

> **Pre-release, not yet tested on a Steam Deck.** Please record a log (Settings → Diagnostics → Record a log) in a game with the Governor on, and send it.

### Changed
- When the Governor is **paused** or **cannot reach the target**, Home now runs **Check setup** once in the background and shows a **"Likely cause"** card with up to two concrete fixes (for example "Start the game with the GFG launch command, then press RUN" or "Turn the overlay on in Settings → In-game overlay"). The button there opens Check setup. If every check passes, it still offers **Record a log**.
- The check runs when the problem appears or its reason changes, not on every status poll.

Everything from v0.0.15 is included.

### Install
1. Download `GFG-Extreme-Governor-v0_0_16.zip` and install it through Decky Loader (install from zip). Accept the root access request.
2. Close the game, press **RUN**, start the game.

### Verify your download
SHA-256 of the zip: `<sha256>` (see `SHA256SUMS.txt`).

### Known limitations
See `docs/GFG_GOVERNOR_KNOWN_LIMITATIONS.md`. The cause shown is the first failed precondition, not a proof of why the Governor paused.
