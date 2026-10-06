## GFG Extreme Decky: Governor v0.0.5 (pre-release)

**In-game overlay fixes from the v0.0.4 field test.**

> **Pre-release.** Please record a log (Home → Record log) and send it.

### Fixed
- **The overlay stays on the side you pick.** MangoHud's horizontal bar used to stretch across the whole screen, so its text started at the left edge whatever the position said. It is now only as wide as its content, so top right and bottom right sit on the right. **Bottom right** is now one of the position choices.
- **FPS with frame generation.** The overlay now leads with the FPS you actually see, generated frames included, then the multiplier and the real (rendered) FPS in brackets: `90 FPS  x2  (45)  sc100  9W …`. MangoHud's own FPS counter is shown only while the Governor has no renderer telemetry, for example when the Governor is off.
- **Live TDP instead of `TDP n/a`** in the overlay.

Everything from v0.0.4 is included (TDP control through the root helper).

### Install
1. Download `GFG-Extreme-Governor-v0_0_5.zip` and install it through Decky Loader (install from zip). Accept the root access request.
2. Close the game, press **RUN**, start the game.

### Verify your download
SHA-256 of the zip: `<sha256>` (see `SHA256SUMS.txt`).

### Known limitations
See `docs/GFG_GOVERNOR_KNOWN_LIMITATIONS.md`. The overlay switches its FPS source by rewriting MangoHud's config, which MangoHud reloads on change; this is not yet verified on Steam Deck hardware.
