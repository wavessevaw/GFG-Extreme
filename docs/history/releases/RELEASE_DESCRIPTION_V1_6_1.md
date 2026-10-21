## GFG Extreme 1.6.1: render scale that is really applied, a faster guard

Fixes from a Steam Deck log on 1.6.0.

### Fixed
- **Lower resolution only when it really happens, in every mode.** In the log the game kept rendering at 1280×800 whatever size the engine offered, yet Battery counted its 90 % and 80 % steps as working and then raised the power limit to 19 W for a resolution change that never happened. Now Battery, Balanced and Extreme accept a lower render scale only when the engine reports that the game renders at it. When the engine says the game ignores the size, the step is dropped at once, and GFG remembers that game and stops trying lower resolutions there (Details and Settings → Scaling say so; *Reset what GFG learned* tries again).
- **No more 75 seconds of short output after a heavy scene.** With about 26 real frames the Governor tried three in-between ratios one after another, each waiting 25 s for a confirmation it could not get. It now goes straight to the ratio the measured real frames can actually hold.
- **Extreme climbs without a restart.** Before the first restart in Extreme (the scaler not loaded yet), Extreme stayed at 45 real frames. It now climbs to more real frames at full resolution. Battery and Balanced also climb back past the lower-resolution steps when those are not available.
- **Log summary:** Extreme's highest power counts only limits GFG wrote (the 20 W in the log was the Deck's own limit before GFG took over). A new line says when a game ignored render scale and why.

### Also
- **In-game overlay:** an `EXT` tag in Extreme, with the render scale once the engine has confirmed it (`EXT 80%`); the TDP ring is drawn against Extreme's ceiling.
- A second way to confirm render scale: the engine's own state file next to its config.

### Install
Download `GFG-Extreme-v1_6_1.zip` below and install it with Decky Loader (*Install from zip*) over your current version. Settings, profiles and everything GFG learned are kept.

### Verify your download
SHA-256 of the zip: `<sha256>` (see `SHA256SUMS.txt`).
