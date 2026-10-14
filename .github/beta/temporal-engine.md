# GFG Extreme 2.1.2-te.3 — Temporal Engine beta (pre-release)

**Experimental build for hardware trials. Not verified on a Steam Deck.** Everything else is GFG Extreme 2.1.1.

te.3 is a **diagnostic** build: te.2 ran on the Deck, but its measurements never reached the plugin, so the logs could not show why motion did not feel smooth or where the artifacts came from.

- **Telemetry fixed.** The engine wrote one status field as `1` instead of `true`, and the plugin rejected the whole record — every te.2 log showed "waiting-for-game". The plugin now accepts both forms (so even the te.2 engine reports), and the te.3 engine writes `true`/`false`.
- **Engine stats in the renderer log** every 10 seconds: quality level, whether it is holding (showing the newest real frame instead of generated ones because it is over the cost cap), GPU time per pair and per generated frame, and the REUSE/LIGHT/FULL shares. The log summary reports them.
- No change to how frames are generated: this build is for measuring what te.2 does on the Deck.

How to test: install **GFG-Extreme-v2_1_2-te_3.zip** through Decky, **Settings → System → Update engine**, restart the game through `/home/deck/.local/bin/gfg %command%`, keep **Temporal Engine · Experimental**, record a log (2–3 minutes in the scene with the shiny surface and the sword), then the same with Temporal Engine **Off**.

SHA-256: `<sha256>` — also see **SHA256SUMS.txt**.
