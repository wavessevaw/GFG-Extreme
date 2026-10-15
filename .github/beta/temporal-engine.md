# GFG Extreme 2.1.2-te.6 — Temporal Engine beta with GFG Shell (pre-release)

**Experimental build for hardware trials.** Everything else is GFG Extreme 2.1.1.

te.6 builds on te.5 (the LMC generator rebuilt for the Steam Deck's GPU) and fixes frame pacing in Autopilot.

**Even frames in Autopilot.** When a game could not hold its frame rate, Autopilot lowered the goal from 90 to 60 FPS while the panel stayed at 90 Hz. 60 FPS on a 90 Hz panel shows frames for one and two refreshes in turn (11 and 22 ms): visible judder whatever the frame generator does. The lowered goal is now 45 FPS, half the refresh, so every frame is shown for exactly two refreshes. An operating point whose real frames times its multiplier would miss that goal (x2 over 22 real frames is 44, not 45) now runs with the exact ratio.

**Steady watts during Autopilot experiments.** While Autopilot measures a change, the power limit is meant to stay constant; Frame OS boost and rest could still move it and spoil the measurement. Now nothing moves it until the experiment ends.

**Cheaper block search.** The frame generator's block search compiled to about 40,000 instructions, far more than the GPU's instruction cache holds. It is now specialised per pyramid level (about 2,000 instructions), and candidates that repeat an earlier one are skipped. The generated frames are bit-identical to te.5.

The picture is the same as te.5 on the seven rendered bench scenes and on real camera footage. The GPU cost on the Deck is still estimated, not measured: about 3–6 ms per frame pair at 1280×800 (te.4 measured 30–70 ms). The renderer log has the GPU time of every analysis pass every 10 seconds (`Temporal Engine stats algo=lmc … lmc_ms=… lmc_passes=…`), and the log summary reports per-pass medians.

**GFG Shell 0.2.3 is included.** The alternative Gaming Mode shell (Godot; Steam stays the game client) installs and launches from the plugin: **GFG Extreme → GFG Shell → Install**, then **Launch**.

How to test: install **GFG-Extreme-v2_1_2-te_6.zip** through Decky, **Settings → System → Update engine**, restart the game through `/home/deck/.local/bin/gfg %command%`, keep **Temporal Engine · Experimental**, record a log of 2–3 minutes of play with camera movement, then the same with Temporal Engine **Off**.

SHA-256: `<sha256>` — also see **SHA256SUMS.txt**.
