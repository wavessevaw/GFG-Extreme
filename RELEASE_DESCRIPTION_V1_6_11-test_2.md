# GFG Extreme 1.6.11-test.2 — Open smoothness and HUD test

> TEST BUILD — EXPERIMENTAL. GFG Open and Extreme remain under development. This is not an official stable release.

Includes the Open cadence-aware GPU guard and reference-patch reuse from test.1. Physical Steam Deck smoothness/performance still needs the user's test.

HUD fixes:
- ENERGY number shows saved TDP allowance against the device's Gamescope/QAM slider maximum (hardware maximum fallback), using unrounded confirmed caps. 20 W maximum / 15 W cap = 25%. Unknown maximum is not replaced with the initial cap.
- ENERGY arc shows battery charge. Green at/above 50%; continuous transition towards red below 50%. It is fully visible regardless of Frame OS state, estimates or whether Frame OS is enabled.
- Game/profile/renderer-session changes reset held FPS and benefit badges. Held FPS cannot verify BOOST; missing Frame OS telemetry clears the active badge.
- Text fallback uses fresh renderer intervals instead of long rolling medians and works in HUD-only sessions.
- Zero TDP is shown as 0W. Invalid/nonfinite values do not break rendering. Detailed BATTERY stays visible while charging and shows charge when remaining time is unavailable.
- Reference layout, glyphs, four corners and cached rendering retained. Explicitly unmeasured RESP/FRAMES values are grey.

Automated backend, HUD native integration, pixel/reference, performance and Open Vulkan tests must pass before publication. On-device validation remains pending.

Install GFG-Extreme-v1_6_11-test_2.zip through Decky Loader and fully restart the game to load native Open build 4.0.0-gfg.open.2. Check camera-motion smoothness versus the ordinary engine and verify that the ENERGY arc follows charge while its centre follows TDP savings.

SHA-256: `<sha256>` (also in SHA256SUMS.txt).
