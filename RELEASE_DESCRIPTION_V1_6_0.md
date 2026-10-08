## GFG Extreme 1.6.0: Extreme mode

A fourth mode for the most real frames on a **stock** Steam Deck. No overclock, no BIOS changes. Extreme puts every watt of the stock limit into real frames instead of saving it.

### New
- **Extreme mode.** The whole power limit goes into real frames: 15 W, or your own lower limit, never more. Every power write is clamped to this one ceiling, Frame OS Act boosts included. Lower the limit in the quick menu while you play and the new value is the ceiling. Real frames stay at 30 or more.
- **Render scale with matched sharpening.** Where it buys more real frames, Extreme renders at 90 % or 80 % and sharpens to match (0.15 / 0.30, adjustable by ±0.3 on Home). Lower resolution is never used in a CPU-bound game or over your profile's own scaling. Sharpening is skipped when your vkBasalt filter already sharpens. Your saved profile is never changed.
- **Confirmed or rolled back.** A new render scale counts only after the engine reports the size the game really renders at. Without that it is rolled back within 20 s. After two misses Extreme stays at full resolution for the session.
- **The wolf in the ring.** In Extreme the GFG wolf sits inside the main ring on Home.
- **Honest boosters.** Home lists the nine Extreme directions and what each does right now: active, waiting, needs a restart, or unavailable with the reason. Background jobs, fan, memory, latency and the stutter shield stay off until they can be done safely and measured on a stock Deck.
- **No promised numbers.** The gain against Balanced is shown only after a same-scene A-B-A check (planned). Battery and Balanced suggest Extreme when a game leaves power unused.
- **Frame OS Act if you want it.** The first switch to Extreme asks once whether Act may join. Leaving Extreme gives the previous Frame OS setting back.

### Good to know
- After switching to Extreme, **restart the game once**. The scaler is loaded at game start; until then Extreme runs at full resolution and says so.
- Extreme uses more battery than Balanced: that is the point of the mode.
- Logs (Settings → Diagnostics → Record log) now include the Extreme state, the ceiling, the highest power cap read and the render scales the engine confirmed. Logs from your games help tune it.

### Install
Download `GFG-Extreme-v1_6_0.zip` below and install it with Decky Loader (*Install from zip*) over your current version. Settings, profiles and everything GFG learned are kept.

### Verify your download
SHA-256 of the zip: `<sha256>` (see `SHA256SUMS.txt`).
