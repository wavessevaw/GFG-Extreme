## GFG Extreme 1.0.6

**Quality mode searches faster and stops repeating what just failed.**

### Improved
- **Quality: faster rejection.** When the renderer takes a requested ratio but holds the target with a deeper one (the GPU cannot feed the requested real frames), Quality now moves on after about 8 s instead of waiting 25 s. Battery and Balanced have done this since 1.0.1. On the Deck log of 2026-10-07 this cost 25 s on 40x2.25.
- **Quality: failure memory.** Points that did not hold in Quality are remembered for 10 minutes per game. Switching to Battery and back, or a plugin reload, no longer starts with the same failed attempts.
- **Session history keeps the game.** The game's Steam AppID is taken when the game starts. Before, the session summary could lose it because the game had already closed when the summary was written.
- **Log summary warns about old recordings.** A log recorded with an older version says so in its first line, since some of what it shows may already be fixed.

Everything from 1.0.5 is included.

### Install
Download `GFG-Extreme-v1_0_6.zip` below and install it through Decky Loader (*Install from zip*) over your current version; settings, profiles and game memory are kept.

### Verify your download
SHA-256 of the zip: `<sha256>` (see `SHA256SUMS.txt`).
