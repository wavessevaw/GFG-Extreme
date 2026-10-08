## GFG Extreme 1.4.1: Frame OS Act stays on

A Steam Deck recording from a heavy DX12 game showed Frame OS Act switching itself off for the whole session, though the game never actually dropped below 90 FPS. 1.4.1 fixes that.

### What happened
When Act starts, the renderer briefly re-plans for its new frame-pacing mode: for a moment, about one second, it shows only the real frames. Act's safety check looked at exactly those one or two samples, called it a starved output and stepped back — twice in that recording, and two strikes lock Act out until the next game. Meanwhile the output stayed at 90 FPS. Because Act was off, the in-game A/B check never got a chance to measure anything either.

### The fix
- After Act starts, its safety check waits four seconds and needs at least three fresh samples before it judges anything.
- A drop counts only when the median output is low **and** the last three samples in a row are low — a renderer re-plan is one or two samples, real starvation is not.
- A real, lasting drop still hands control back to the Governor at once, exactly as before.

### Install
Download `GFG-Extreme-v1_4_1.zip` below and install it with Decky Loader (*Install from zip*) over your current version; settings, profiles and what GFG learned are kept. Restart a running game so its layers update.

### Verify your download
SHA-256 of the zip: `<sha256>` (see `SHA256SUMS.txt`).
