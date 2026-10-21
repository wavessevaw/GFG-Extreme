# GFG Extreme 2.1.0 — stable

This stable build brings the completed spatial and native-resolution Frame Fusion paths together with short Boost. **Fusion and Boost work only in Autopilot.** Leaving the mode closes the shortcuts and cancels Boost; Battery, Balanced and Quality keep their normal paths.

- Autopilot feature switches default on: Fusion, short Boost, right-stick touch, frame timing, Stall Shield and compatible Half Rate Shading trials. Existing saved off choices are preserved; compatibility, power and temperature checks remain.
- Right-stick touch requests an early 500 ms pulse. Motion/camera/action can request up to 1.5 seconds, then return to calm with a recovery gap. Holding the stick or finger cannot create permanent Boost.
- Short real-present windows replace the long cadence median for burst qualification. Unsuccessful exposure is counted across distinct pulses. A request/ACK is not reported as a measured speedup.
- Fusion uses compatible direct spatial inputs or same-format native copies. The Deck logs confirmed Native Fusion executes; comparative FPS/energy/latency gain has not been established.
- Recording before a new game launch now preserves rotated diagnostic segments. Exports identify missing/truncated data, and summaries flag generated-frame delivery misses.
- Half Rate Shading power decisions use renderer-aligned median windows; acceptance events retain the exact evidence used.
- Updated Autopilot cards, README and the visible **stable** profile label. Saved profile identifiers and launch commands are compatible.

## Install

Install **GFG-Extreme-v2_1_0.zip** with Decky, close games, install/update the bundled engine and relaunch through `/home/deck/.local/bin/gfg %command%`. Choose Autopilot and Run. Users on 2.1.1/2.2.0 previews should install this ZIP explicitly: the requested stable version is 2.1.0.

The package contains both Fusion paths, verified native payload identities, existing 32-bit/Flatpak fallback payloads and the Frame OS/HUD layers. Licensed Lossless Scaling models are not bundled. Automated checks run before publication; the new touch pulse still requires repeated hardware field comparisons before claiming performance or energy gains.

SHA-256: `<sha256>` — also see **SHA256SUMS.txt**.
