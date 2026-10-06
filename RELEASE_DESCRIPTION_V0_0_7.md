## GFG Extreme Decky: Governor v0.0.7 (pre-release)

**TDP is now set the way Steam's own slider sets it.**

> **Pre-release, not yet tested on a Steam Deck.** Please record a log (Home → Record log) in a game with the Governor on, and send it.

### Changed
- **TDP goes through `steamos-manager`.** Up to v0.0.6 the Governor wrote the Steam Deck power-limit files directly. That bypasses `steamos-manager`, the service behind Steam's TDP slider, so Steam kept showing (and applying) its own limit, for example 20 W. The Governor now sets the TDP through the same service (`steamosctl set-tdp-limit`, or D-Bus `TdpLimit1`), the method of the earlier GFG Extreme efficiency monitor that changed the TDP on a real Deck. Steam's quick menu and performance overlay show the value the Governor set.
- Values are whole watts, and every change is read back from the power-limit files. If the service accepts a value but the limit does not change, that is reported as an error, not as success.
- Writing the files directly (through the root helper) stays as a fallback when `steamos-manager` has no TDP interface or refuses.
- The log shows which method was used (`tdp_method` in the timeline, `method` in the action journal).

Everything from v0.0.6 is included (Battery mode, measured APU draw, power sensors in the log).

### Install
1. Download `GFG-Extreme-Governor-v0_0_7.zip` and install it through Decky Loader (install from zip). Accept the root access request.
2. Close the game, press **RUN**, start the game.

### Verify your download
SHA-256 of the zip: `<sha256>` (see `SHA256SUMS.txt`).

### Known limitations
See `docs/GFG_GOVERNOR_KNOWN_LIMITATIONS.md`. Not yet verified on hardware: that the plugin process reaches `steamosctl` and the session bus after it switches to your user.
