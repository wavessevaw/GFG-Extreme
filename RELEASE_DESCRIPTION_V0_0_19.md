## GFG Extreme Decky: Governor v0.0.19 (pre-release)

**Fixes from the second Steam Deck log** (Witcher 3, Steam Deck OLED, 15 minutes, Balanced and Battery). Thank you for sending it.

> **Pre-release.** Please keep sending logs (Settings → Diagnostics → Record a log).

### What the log showed
- **v0.0.17's fix works.** Balanced asked for 40×2.25, the renderer delivered 90 FPS at 33 real frames, and the Governor followed it down to 33×2.75 and then 30×3, holding **90 FPS at 13 W**. In the first log the same situation ended at 15 W and about 80 FPS.
- Battery held **90 FPS at 30×3 and 10 W**; Check setup was all green; no crash.
- **New problem: ratios deeper than ×3.** In a heavy scene Battery tried 28×3.25, then 26×3.5, then 24×3.75. The renderer has resources for at most **two generated frames per real frame** (×3); more needs a swapchain recreation. So each request fell back to a fixed ×3 at fewer real frames: **84, 78 and 72 FPS on screen**, 25 seconds each, before the Governor gave up and added watts.

### Fixed
- **The Governor reads the renderer's generated-frame capacity** from its own diagnostics and never offers a ratio beyond it. In that scene it now adds watts at ×3 straight away instead of three 25-second drops to 72–84 FPS. If the current target is beyond the capacity, it falls back at once.
- **Log verdict** reports when requests needed more generated frames than the renderer had.

Everything from v0.0.18 is included.

### Install
1. Download `GFG-Extreme-Governor-v0_0_19.zip` and install it through Decky Loader (install from zip). Accept the root access request.
2. Close the game, press **RUN**, start the game.

### Verify your download
SHA-256 of the zip: `<sha256>` (see `SHA256SUMS.txt`).

### Known limitations
See `docs/GFG_GOVERNOR_KNOWN_LIMITATIONS.md` (item 26). A fractional point the GPU cannot feed still costs one 25 s confirmation (output stays at the target meanwhile).
