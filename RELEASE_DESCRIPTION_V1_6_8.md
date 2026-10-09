# GFG Extreme 1.6.8 — stable fixes for 1.6.5

This official stable update uses the 1.6.5 renderer and configuration base. The experimental GFG Open generator from 1.6.6/1.6.7 is not included.

- **Late real-frame pacing:** Frame OS releases a ready late frame immediately and re-anchors its schedule. Missing a frame-start deadline no longer adds a second full-slot wait. A deterministic 34 ms workload under a 30 Hz policy ran at 15.007 FPS with the old scheduler and 29.412 FPS after the fix. This is a code-level regression test, not a Steam Deck field benchmark.
- **Energy number:** shows the percentage of TDP cap saved relative to SteamOS Manager's Gamescope/QAM slider maximum, with the hardware maximum as fallback. A 15 W cap under a 20 W slider maximum shows **25%**. Ring arcs, colours and layout are unchanged; this number is cap savings, not measured battery energy.
- **CPU restoration:** accepted helper writes retain ownership while readback is stale, allowing late own writes to be restored across all CPU policies. Diagnostics expose observed and pending policy caps.
- **A/B statistics:** current measured benefits require this session's control pairs. Historical results stay separate.
- **Extreme mode:** remains **BETA / EXPERIMENTAL**, in development and not recommended for regular play. Its label appears in the selector, booster card, description and invitation. A stable package does not mean every experimental mode is production-ready.

Install **GFG-Extreme-v1_6_8.zip** through Decky Loader → Install from zip, then restart the game to load the updated Frame OS layer. Users testing GFG Open in 1.6.6/1.6.7 should also reinstall the bundled 1.6.5 renderer through the plugin's engine installer before restarting; updating Decky files alone does not replace an already installed renderer.

Validation covers backend tests, native Frame OS and HUD integration, scheduler regression reproduction, frontend smoke and the actual packaged ZIP. A comparable Steam Deck retest is still needed to quantify field FPS; this release makes no claim that every reported frame drop is resolved.

SHA-256: `<sha256>` (also in SHA256SUMS.txt).
