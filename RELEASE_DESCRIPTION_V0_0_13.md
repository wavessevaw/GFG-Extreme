## GFG Extreme Decky: Governor v0.0.13 (pre-release)

**Every recorded log now explains itself.**

> **Pre-release, not yet tested on a Steam Deck.** Please record a log (Settings → Diagnostics → Record a log) in a game with the Governor on, and send it.

### New
- **"What the log shows".** After **Stop and save log to Desktop**, the screen lists up to four findings from the log: no renderer diagnostics written, diagnostics without any FPS reading, telemetry stale for long stretches, the Governor paused most of the time (and the most common reason), operating points the renderer did not confirm, failed self-test checks (for example "overlay config published"), output FPS against the target, an overheating APU.
- **`summary.txt` inside every log zip**, with the same verdict plus states, reasons, points used, real/output FPS, TDP range, temperature, bottlenecks and a count of renderer operations. The renderer lines in the log are run through the same parser the Governor uses, so the report shows exactly what the Governor could see.
- **`tools/gfg_log_report.py`** prints the report for any log zip on a PC.

Everything from v0.0.12 is included.

### Install
1. Download `GFG-Extreme-Governor-v0_0_13.zip` and install it through Decky Loader (install from zip). Accept the root access request.
2. Close the game, press **RUN**, start the game.

### Verify your download
SHA-256 of the zip: `<sha256>` (see `SHA256SUMS.txt`).

### Known limitations
See `docs/GFG_GOVERNOR_KNOWN_LIMITATIONS.md` (item 23). The verdict states what the log contains, not why; its thresholds are rules of thumb.
