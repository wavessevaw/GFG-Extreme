## GFG Extreme Decky — Governor v0.0.2 (pre-release)

A continuation of the **MAKO** and **LSFG** work for the Steam Deck. This release turns the Governor into a one-button experience: pick a profile, press **RUN**, and the engine chooses the target for your setup (**OLED 90 / LCD 60 / Dock 60**) and tunes itself.

> **Pre-release.** Not yet validated on Steam Deck hardware. Please record a log and send it (see below).

### Highlights

- **One Run button.** The new interface is built around a single action. Near-black design with the logo-red accent.
- **Touch and controller.** Buttons work with touch and with **A** (and Enter); the segmented and ± controls are focusable.
- **Smart operating points.** The Governor tries the highest-quality setting first: **native**, then fractional multipliers **×1.25 to ×2.75** in quarter steps, then **×2 with a reduced render scale** before heavy generation, and **×3 at most**. Never ×4 or ×5. Points the observed native cadence already rules out are skipped instead of being trialled.
- **It mostly does nothing.** Each change is confirmed on real renderer data, rolled back if it fails, and left alone once the target is held.
- **Your Saved profile is never modified.** The Governor works through a temporary overlay that is removed when it stops.
- **Power aware.** After the point is confirmed, TDP is lowered step by step as far as the target allows, and always restored.
- **Compact in-game overlay.** FPS, frame time, multiplier, real → output FPS, render scale, current **TDP**, **battery time left** and **GFG Effort**, with MangoHud's native GPU power and battery sensors. No CPU load readout.
- **GFG Effort rating.** Easy / Medium / Hard / Nightmare, shown only once it is stable. A game that already holds the target is never rated Nightmare.
- **Copyable launch command** (Home, step 1, and Advanced), with a clear fallback message.
- **Clear Frame Generation labels:** GFG Engine / OptiScaler / In-game / Off, each explained.
- **New logo and README** in English and Russian.

### Record log
Home → **Record log** → play for a minute or two → **Stop and save log to Desktop**.
A zip `GFG-Extreme-log-<date>.zip` is written to the Steam Deck desktop (`~/Desktop`). It contains a 1 Hz Governor timeline, the renderer diagnostics captured during the recording, Governor decisions, the generated launch wrapper, overlay files, the saved profile, a self-test of every precondition and basic system info. No personal data beyond file paths.

### Install
1. Download `GFG-Extreme-Governor-v0_0_2.zip` and install it through Decky Loader (install from zip).
2. Open the plugin, **Install engine** if asked, copy the launch command into the game's Steam launch options, relaunch the game, press **RUN**.

### Verify your download
SHA-256 of the zip: see `SHA256SUMS.txt` in the assets.

### Known limitations
See `docs/GFG_GOVERNOR_KNOWN_LIMITATIONS.md`. Native (x1) telemetry and the MangoHud `exec` refresh rate remain unverified until a log from a real Deck is available. 218 automated tests, all passing. Renderer and Flatpak extensions are byte-identical to Beta.2.
