## GFG Extreme Decky: Governor v0.0.11 (pre-release)

**The Governor remembers what worked for a game, so the next session starts there instead of searching.**

> **Pre-release, not yet tested on a Steam Deck.** Please record a log (Settings → Diagnostics → Record a log) in a game with the Governor on, and send it.

### Changed
- **Game memory.** Once a point has held for 90 s, its operating point and TDP are stored per profile, display target and mode (`gfg-game-models.json`, at most 200 entries, 30 days). The next session starts locked on that state: no settle phase, no walk down from 10 W.
- **Safe by construction.** The remembered state goes through the same lock and guard as a fresh one. If the game is heavier today, the guard adds watts or a deeper ratio within seconds; if it is lighter, the 45 s probes lower the watts again. Only normal points are remembered (never the last-resort point), the TDP is clamped to what the Deck allows without the emergency range, and nothing is stored while another tool overrides the cap.
- **Visible.** Home says "Started from what worked last time", Details shows **Start: Remembered / Searched from scratch**, and the log records a `budget-warm-start` event.

Everything from v0.0.10 is included.

### Install
1. Download `GFG-Extreme-Governor-v0_0_11.zip` and install it through Decky Loader (install from zip). Accept the root access request.
2. Close the game, press **RUN**, start the game.

### Verify your download
SHA-256 of the zip: `<sha256>` (see `SHA256SUMS.txt`).

### Known limitations
See `docs/GFG_GOVERNOR_KNOWN_LIMITATIONS.md` (item 21). The memory key is the profile name, so several games sharing one profile share one memory.
