## GFG Extreme Decky — Governor v0.0.3 (pre-release, fixes for v0.0.2)

v0.0.2 was never run on a Steam Deck and several things did not work. This release fixes what could be found by reading the code, and adds a **log recorder** so the rest can be diagnosed from a real device.

> **Pre-release.** Still not validated on hardware. Please record a log and send it (see below).

### Fixed
- **Controller / Steam Deck buttons.** The interface reacted only to touch. Buttons now activate with **A** (and Enter), and the segmented / ± controls are focusable.
- **Live numbers on Home and in the in-game overlay.** The UI and overlay read telemetry in the wrong shape, so REAL → ×N → OUTPUT and the overlay FPS line stayed empty. Fixed, with a contract test.
- **Nightmare at a stable 90 FPS.** A game that already holds the target is no longer rated Nightmare just because no point was accepted.
- **Faster operating-point search.** Points that the observed native cadence already rules out are skipped (not rejected) instead of being trialled for 25–60 s each.
- **Launch command is copyable** (Home, step 1, and Advanced), with a clear fallback message.
- **Clearer Frame Generation labels** (GFG Engine / OptiScaler / In-game / Off, each explained).
- **Overlay config** also includes MangoHud's native GPU power and battery sensors.

### New: Record log
Home → **Record log** → play for a minute or two → **Stop and save log to Desktop**.
A zip `GFG-Extreme-log-<date>.zip` is written to the Steam Deck desktop (`~/Desktop`). It contains a 1 Hz Governor timeline, the renderer diagnostics captured during the recording, Governor decisions, the generated launch wrapper, overlay files, the saved profile, a self-test of every precondition and basic system info. No personal data beyond file paths.

### Install
1. Download `GFG-Extreme-Governor-v0_0_3.zip` and install it through Decky Loader (install from zip).
2. Open the plugin, **Install engine** if asked, copy the launch command into the game's Steam launch options, relaunch the game, press **RUN**.

### Known limitations
See `docs/GFG_GOVERNOR_KNOWN_LIMITATIONS.md`. Native (x1) telemetry and the MangoHud `exec` refresh rate remain unverified until a log from a real Deck is available.
