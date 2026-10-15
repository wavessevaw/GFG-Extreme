# GFG Extreme 2.1.2-te.4 — Temporal Engine beta with GFG Shell (pre-release)

**Experimental build for hardware trials. Not yet verified on a Steam Deck.** Everything else is GFG Extreme 2.1.1.

te.4 replaces the frame generator. The tile engine of te.1–te.3 is still there (`GFG_TEMPORAL_ALGO=tiles`), but the default is now **LMC, layered motion compensation**:

- **The HUD is not warped.** Pixels that stay still for several pairs while the scene moves are copied from the newest real frame.
- **Camera motion is one model per surface.** Up to three robust homographies (RANSAC + IRLS) give every background pixel an exact, sub-pixel vector with no tile grid and no range limit.
- **Objects get their own vectors.** A predictive block search (3-D recursive search style, spatial propagation, vector median), a motion palette (the most frequent vectors, so a still object over a moving scene keeps no halo) and a wide search for blocks nothing else explains.
- **Edges pick the right frame.** Each output pixel tests candidate trajectories: valid in both frames → blend; only in the previous one → it is being covered, take it from there; only in the newest → it is being uncovered. The tile engine chose the side by time, which is wrong on half of every moving edge.
- **No cost hold.** The tile engine repeated the real frame for 120 pairs whenever it went over its cost cap; LMC never does.

On the offline bench (rendered 90 FPS scenes, every third frame kept, the two between generated and compared with what was really rendered; NVIDIA FLIP, lower is better) LMC beats the tile engine and an FSR 3 frame-interpolation port without game vectors in camera pans, orbits, walks through thin posts, glossy surfaces and HUD, and ties on particles. A fast rotating thin blade is still hard for every generator.

**GFG Shell 0.2.3 is included.** The alternative Gaming Mode shell (Godot; Steam stays the game client) installs and launches from the plugin: **GFG Extreme → GFG Shell → Install**, then **Launch**. Home with the game in focus and recently played, the library with filters, the game page with GFG Autopilot, search with an on-screen keyboard, downloads, settings, the side menu, quick settings and the power menu. A and B work on the pad, modal menus keep focus, recently played follows Steam's own records, every installed game is listed, and non-Steam shortcuts launch and return cleanly.

The renderer log now has the engine's real GPU time per stage every 10 seconds (`Temporal Engine stats algo=lmc … pyramid_ms analyze_ms fields_ms frame_ms pair_p95_ms layers orphans`), and the log summary reports it: one recording answers whether it fits the Deck's budget.

How to test: install **GFG-Extreme-v2_1_2-te_4.zip** through Decky, **Settings → System → Update engine**, restart the game through `/home/deck/.local/bin/gfg %command%`, keep **Temporal Engine · Experimental**, record a log of 2–3 minutes of play with camera movement, then the same with Temporal Engine **Off**.

SHA-256: `<sha256>` — also see **SHA256SUMS.txt**.
