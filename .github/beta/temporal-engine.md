# GFG Extreme 2.1.2-te.2 — Temporal Engine beta (pre-release)

**Experimental build for hardware trials. Not verified on a Steam Deck.** Everything else is GFG Extreme 2.1.1.

te.1 could cost more GPU time than regular frame generation. te.2 targets *no more GPU time than regular frame generation*:

- **Cost cap**: the engine may use at most **2 ms of GPU time per generated frame** (`GFG_TEMPORAL_CAP_MS` to change it). Over the cap it steps down at once, to LIGHT-only (no FULL tiles). If even that is over the cap, it holds — shows the newest real frame without analysis — for about 4 seconds, then measures again.
- **Motion analysis** runs 64 threads per tile instead of one (same result, far better GPU occupancy).
- **FULL tiles** take one decision per 2×2 pixels (quality within 0.05 dB in the bench, a quarter of the search work).
- **Telemetry now works in Steam Runtime games**: the Diagnostics panel and logs show GPU time per stage, class shares, level, the cap and cost holds. The panel says when a changed mode waits for a game restart.
- The bundled engine reports its own version (`4.0.0-gfg.fusion.3-te.2`), so Settings → System shows when it needs **Update engine**.

Off by default; pick a mode in **Settings → Diagnostics → Temporal Engine · Experimental**. Each choice applies from the next game start.

Whether the cap of 2 ms per frame is at or below regular frame generation on the Deck is not measured yet: compare real FPS with Off and with Experimental in the same scene. No FPS, latency or battery gain is claimed. Interpolation always adds at least one real-frame interval of latency.

Install **GFG-Extreme-v2_1_2-te_2.zip** through Decky, then **Settings → System → Update engine**, then restart the game through `/home/deck/.local/bin/gfg %command%`. To go back, install the 2.1.1 release and update the engine again.

SHA-256: `<sha256>` — also see **SHA256SUMS.txt**.
