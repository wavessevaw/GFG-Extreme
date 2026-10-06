## GFG Extreme Decky: Governor v0.0.12 (pre-release)

**A third mode: Balanced, between maximum battery and maximum quality.**

> **Pre-release, not yet tested on a Steam Deck.** Please record a log (Settings → Diagnostics → Record a log) in a game with the Governor on, and send it.

### New
- **Balanced mode** (Home → Mode: Battery / Balanced / Quality). It uses the same engine as Battery, with a higher floor:
  - starts at about **45 real FPS and 12 W** (×2 on a 90 Hz screen) instead of 30 real and 10 W;
  - **never below 30 real FPS** (no ×3.25 to ×3.75, no last-resort ratio);
  - **never above your Deck's normal power range**: no emergency watts;
  - still reacts within seconds and still lowers watts in 1 W probes while the game holds.
- Game memory is stored per mode, so switching modes does not mix up what was learned.

Everything from v0.0.11 is included.

### Install
1. Download `GFG-Extreme-Governor-v0_0_12.zip` and install it through Decky Loader (install from zip). Accept the root access request.
2. Close the game, press **RUN**, start the game.

### Verify your download
SHA-256 of the zip: `<sha256>` (see `SHA256SUMS.txt`).

### Known limitations
See `docs/GFG_GOVERNOR_KNOWN_LIMITATIONS.md` (item 22). The Balanced numbers are design choices, not yet tuned on real games.
