## GFG Extreme 1.0.2

**Smarter memory, clearer screens, better logs, and LCD/dock starts — mostly from the two recorded Witcher 3 sessions.**

### The Governor
- **Game memory per game, not per profile.** When the game was started from Steam, memory is keyed by its Steam AppID, so several games sharing one profile no longer share what was learned. Without an AppID it falls back to the profile, as before.
- **It no longer repeats a probe that just failed.** In a recorded session "fewer generated frames" (33×2.75 at 10 W) was tried three times, because every mode switch starts a fresh search. Failed probes are now remembered per game for 15 minutes (with the TDP they failed at), so a mode switch or plugin reload skips them; with more watts, or after 15 minutes when the scene may be lighter, they are tried again.
- **60 Hz screens (Steam Deck LCD, dock): Balanced starts on 30×2 instead of 48×1.25.** Both modes now start on a whole-number ratio: on a Deck those confirmed in about 10 s, while fractional ratios often ran into the 25 s timeout. Fractional ratios remain available when the Governor tries fewer generated frames. 90 Hz starts are unchanged (30×3 Battery, 45×2 Balanced).

### The interface
- **"Waiting for the game to draw frames (loading screen or menu)"** instead of "the engine reports no FPS — is frame generation on?" during loading screens: that was normal, not an error.
- **"Testing ×2.75 — a few seconds"** while a setting is being confirmed.
- **Details** shows what the Governor knows: a point it is still *verifying*, the deepest ratio the engine allows right now ("up to ×3"), and probes that recently failed ("×2.75 at ≤10 W").

### Logs
- `summary.txt` and the post-recording card now report how much of the session was spent waiting for confirmations (with the reasons) and how often the mode was switched.

### Install
Download `GFG-Extreme-v1_0_2.zip` below and install it through Decky Loader (*Install from zip*) over your current version; settings, profiles and game memory are kept.

### Verify your download
SHA-256 of the zip: `<sha256>` (see `SHA256SUMS.txt`).
