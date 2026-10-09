## GFG Extreme 1.6.2: Frame OS Act boosts only where they can help

More fixes from the same Steam Deck log (a heavy game that gets about 26 real frames).

### Fixed
- **No boost without GPU headroom.** Frame OS Act raised the real-frame target on every camera swing (to 60 or 45 real) while the game did not even reach the calm target. No real frames came, only a rougher output. A boost now needs the calm target to be delivered first, judged on the engine's own real frame rate.
- **Useless boosts stop.** A boost that brings no real frames is paused for two minutes. The check used to need three seconds of uninterrupted boost, which short fight boosts never reached; it now adds up the boost time across a minute.
- **"At the limit" instead of "Protecting".** When a game cannot hold even the deepest setting at the available power, Home now says so, with the real frames it gets, and suggests lower graphics settings in the game. It used to keep saying that a scene got heavier.
- **Extreme:** when a game ignores render scale, its Upscale line says that, not "your profile scales itself".

### Install
Download `GFG-Extreme-v1_6_2.zip` below and install it with Decky Loader (*Install from zip*) over your current version. Settings, profiles and everything GFG learned are kept.

### Verify your download
SHA-256 of the zip: `<sha256>` (see `SHA256SUMS.txt`).
