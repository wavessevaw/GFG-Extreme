## GFG Extreme Decky: Governor v0.0.8 (pre-release)

**The Governor turns on in a game that is already running. No more close game → RUN → start game.**

> **Pre-release, not yet tested on a Steam Deck.** Please record a log (Home → Record log) in a game where you pressed RUN mid-game, and send it.

### Changed
- **RUN works mid-game.** Every game started with the GFG launch command now carries what the Governor needs from the first frame: the renderer's FPS telemetry and a Governor config file the renderer watches. While the Governor is off, that file is an exact copy of your saved settings, so nothing changes in the game. Pressing RUN only changes live settings (multiplier, FPS caps) inside it; TDP goes through `steamos-manager` as before.
- **In-game overlay turns on and off live.** MangoHud is loaded with a hidden config and re-reads it, so the overlay switch works while the game runs.
- Settings you change in the plugin while the Governor is off still reach the running game right away (the Governor copies them into its file).
- When the plugin stops or reloads, new launches go back to the saved settings directly; a running game keeps a valid config.

### Still needs one relaunch
- A game started **before installing v0.0.8**, without the `gfg %command%` launch option, or while the plugin was not running.
- Turning **Frame Generation provisioning** or the **Scaling Engine** (Scale-ready launch) on or off: the renderer builds these once per game process.

Everything from v0.0.7 is included (TDP through `steamos-manager`, Battery mode, measured APU draw).

### Install
1. Download `GFG-Extreme-Governor-v0_0_8.zip` and install it through Decky Loader (install from zip). Accept the root access request.
2. Start the game once with the GFG launch option. From then on press **RUN** whenever you like.

### Verify your download
SHA-256 of the zip: `<sha256>` (see `SHA256SUMS.txt`).

### Known limitations
See `docs/GFG_GOVERNOR_KNOWN_LIMITATIONS.md`. Renderer diagnostics are now on for every managed game (a small log in `~/.config/mako-render`, last 5 sessions kept).
