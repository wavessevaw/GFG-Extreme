# GFG Extreme 2.1.2-te.5 — Temporal Engine beta with GFG Shell (pre-release)

**Experimental build for hardware trials.** Everything else is GFG Extreme 2.1.1.

te.5 is the LMC generator of te.4 rebuilt to fit the Steam Deck's GPU. te.4's analysis passes cost far more GPU time than planned: a few passes ran as one long serial chain on a single compute unit, or did thousands of memory reads per thread, so the game lost frames to the generator. Each pass was checked against the RADV compiler for the Deck's GPU (registers, spills, scratch memory) and reorganised:

- **Object search**: at most 256 blocks per frame, the strongest first, each searched by a whole workgroup instead of one thread. Weak "objects" turned out to be noise; dropping them slightly improves the picture.
- **Per-pixel vectors**: every thread busy, candidate lists built in parallel, the second pass only tries the object vectors.
- **Motion planes**: the fit keeps every block in registers and never waits on memory; reductions are batched.
- **Block search and trajectory test**: whole-pixel candidates read a block with 4 gathers instead of 16 fetches, repeated candidates are skipped, nothing spills to scratch memory.
- **Cost guard**: if a frame pair keeps taking more than a quarter of the real frame interval on the GPU (`GFG_TEMPORAL_LMC_BUDGET`, default 0.25), the generator holds for 120 pairs and measures again, so the game keeps its GPU time.

The picture is the same or slightly better than te.4 on all seven bench scenes (rendered 90 FPS scenes, every third frame kept, the two between generated and compared with what was really rendered; NVIDIA FLIP).

The GPU cost on the Deck is estimated from the work each pass does, not yet measured: about 3–4 ms per frame pair at 1280×800, against 30–70 ms for te.4. The renderer log now has the GPU time of every analysis pass every 10 seconds (`Temporal Engine stats algo=lmc … lmc_ms=… lmc_passes=search_b/search_a/layers/palette/field/masked/orphan/field2`), and the log summary reports per-pass medians: one recording settles it.

**GFG Shell 0.2.3 is included.** The alternative Gaming Mode shell (Godot; Steam stays the game client) installs and launches from the plugin: **GFG Extreme → GFG Shell → Install**, then **Launch**.

How to test: install **GFG-Extreme-v2_1_2-te_5.zip** through Decky, **Settings → System → Update engine**, restart the game through `/home/deck/.local/bin/gfg %command%`, keep **Temporal Engine · Experimental**, record a log of 2–3 minutes of play with camera movement, then the same with Temporal Engine **Off**.

SHA-256: `<sha256>` — also see **SHA256SUMS.txt**.
