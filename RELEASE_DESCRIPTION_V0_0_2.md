## GFG Extreme Decky — Governor v0.0.2 (pre-release)

A continuation of the **MAKO** and **LSFG** work for the Steam Deck. This release turns the Governor into a one-button experience: pick a profile, press **RUN**, and the engine chooses the target for your setup (**OLED 90 / LCD 60 / Dock 60**) and tunes itself.

> **Pre-release.** Not yet tested on Steam Deck hardware. Please read the known limitations before relying on it.

### Highlights

- **One Run button.** The new interface is built around a single action. Near-black design with the logo-red accent.
- **Smart operating points.** The Governor tries the highest-quality setting first: **native**, then fractional multipliers **×1.25 to ×2.75** in quarter steps, then **×2 with a reduced render scale** before heavy generation, and **×3 at most**. Never ×4 or ×5.
- **It mostly does nothing.** Each change is confirmed on real renderer data, rolled back if it fails, and left alone once the target is held.
- **Your Saved profile is never modified.** The Governor works through a temporary overlay that is removed when it stops.
- **Power aware.** After the point is confirmed, TDP is lowered step by step as far as the target allows, and always restored.
- **Compact in-game overlay.** FPS, frame time, multiplier, real → output FPS, render scale, current **TDP**, **battery time left** and **GFG Effort**. No CPU load readout.
- **GFG Effort rating.** Easy / Medium / Hard / Nightmare, shown only once it is stable, so it does not flicker.
- **New logo and README** in English and Russian.

### Install

1. Download `GFG-Extreme-Governor-v0_0_2.zip` from the assets below.
2. Install it as a Decky Loader plugin from zip.
3. Open the plugin and press **RUN**.

### Verify your download

SHA-256 of the zip: `ade10c72bbdbf433bcac88726532bdce683bfb795d586a340d08af63b29741c1` (see `SHA256SUMS.txt`).

### Also in the assets

- `GFG-Extreme-Governor-v0_0_2-from-Beta_2.patch` — source changes since Beta.2.
- `GFG_GOVERNOR_V0_0_2_TEST_REPORT.md` — 207 automated tests, all passing.
- `GFG_GOVERNOR_V0_0_2_KNOWN_LIMITATIONS.md` — what is still unverified on hardware.

Renderer and Flatpak extensions are byte-identical to Beta.2.
