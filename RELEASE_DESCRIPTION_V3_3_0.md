# GFG Extreme 3.3.0

**GFG Extreme 3.3.0 combines the stable GFG Extreme 3.2.2 application with GSF Kedavra 1.5.0.** The engine continues the Silk 1.4.0 line.

## What improved

- **Clearer detail during fast, reliably reconstructed motion.** Kedavra now reduces its existing motion blur only where source samples and neighbouring motion vectors agree.
- **Conservative reconstruction elsewhere.** Uncertain motion and conflicting image regions retain the previous handling.
- **No extra GPU passes or image buffers.** The change reuses existing texture samples in the reconstruction shader.
- **The familiar 3.2.2 application remains.** This release preserves its interface, settings, generation modes, per-game profiles, Autopilot/Governor controls, graphics filters, HUD, diagnostics and engine recovery mechanisms.

There is no new collection of quality sliders to configure. The earlier experimental colour-range clamp is not included.

## Validation and measured results

In a reproducible synthetic fast-pan test at 1280×800, the new engine improved generated-frame PSNR by **3.68–4.20 dB** and reduced mean absolute RGB error by approximately **80%**. These are software Vulkan measurements for that test scene, not a promise of the same improvement in every game.

The engine passed its normal and low-source-FPS software suites. GFG CI passed backend tests, control-system simulations, frontend build/smoke checks, the Gamescope build and runtime library checks. The published installer was also checked for ZIP integrity and a matching SHA256 checksum.

## Known limitations

Block-shaped artifacts during complex camera turns below 30 source FPS remain an open limitation. This release's main demonstrated improvement is fast-motion sharpness, rather than a general solution to ghosting, occlusion or low-FPS artifacts.

This release does not claim hardware validation of Steam Deck GPU performance, power use, physical display pacing or input-to-photon latency. Software test results must not be interpreted as device measurements.

## Installation and rollback

1. Download `GFG-Extreme-v3_3_0.zip`; use `SHA256SUMS.txt` if you want to verify the download.
2. Install it through **Decky Loader → Settings → Developer → Install Plugin from ZIP**.
3. Open GFG Setup, update/install the engine and reboot when prompted.
4. Confirm that Setup reports the installed runtime matching the plugin before testing.

Retain the official 3.2.2 installer and a settings backup. To return to 3.2.2, restore the stock engine through Setup and reboot, then install the 3.2.2 plugin and its engine.
