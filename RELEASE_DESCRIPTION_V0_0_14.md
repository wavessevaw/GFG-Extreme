## GFG Extreme Decky: Governor v0.0.14 (pre-release)

**Documentation that matches the product, and an interface that cannot pile up requests.**

> **Pre-release, not yet tested on a Steam Deck.** Please record a log (Settings → Diagnostics → Record a log) in a game with the Governor on, and send it.

### Changed
- **README (English and Russian)** now describes what the product does today: the three modes, the adaptive loop, game memory, the host sensors and verdict, and a new section **"Something not working? Record a log"** with what the zip contains and how to read it.
- **UI notes** (`docs/GFG_UI_REDESIGN.md`) describe the current navigation and its rules instead of the old redesign plan.
- **Status polling** keeps at most one call in flight and gives up after 10 s, so a slow backend no longer stacks up a request every 1.5 s.

Everything from v0.0.13 is included.

### Install
1. Download `GFG-Extreme-Governor-v0_0_14.zip` and install it through Decky Loader (install from zip). Accept the root access request.
2. Close the game, press **RUN**, start the game.

### Verify your download
SHA-256 of the zip: `<sha256>` (see `SHA256SUMS.txt`).

### Known limitations
See `docs/GFG_GOVERNOR_KNOWN_LIMITATIONS.md`. No release has been validated on a real Steam Deck yet.
