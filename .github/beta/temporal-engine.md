# GFG Extreme 2.1.2-te.1 — Temporal Engine beta (pre-release)

**Experimental build for hardware trials. Not verified on a Steam Deck.** Everything else is GFG Extreme 2.1.1.

The GFG Temporal Engine is a new open frame generator in the bundled engine. It is **off by default**; nothing changes until you pick a mode in **Settings → Diagnostics → Temporal Engine · Experimental**.

- **Observe**: checks whether a game could use the engine. No extra GPU work.
- **Shadow**: runs next to regular frame generation on private images and measures its own GPU cost. Your frames still come from regular frame generation.
- **Experimental** (asks for confirmation): replaces regular frame generation in compatible SDR games. Anything incompatible keeps regular frame generation.

Each choice applies from the next game start. While the engine runs, Autopilot starts no GPU clock, shading or flow trial. The engine's numbers are in the panel and in recorded logs.

Measurements so far come from a CPU Vulkan emulator, not from a Deck. No FPS, latency or battery gain is claimed. Interpolation always adds at least one real-frame interval of latency. Details: `docs/TEMPORAL_ENGINE.md` and `docs/TEMPORAL_ENGINE_BENCHMARK.md`.

**Trial steps**: record a log with Off, then Observe, Shadow (≈10 min) and Experimental (Off → Experimental → Off, ≥3 min each in the same scene), and attach the logs.

Install **GFG-Extreme-v2_1_2-te_1.zip** through Decky (developer mode → install from ZIP), update the bundled engine when prompted, and restart the game through `/home/deck/.local/bin/gfg %command%`. To go back, install the 2.1.1 release.

SHA-256: `<sha256>` — also see **SHA256SUMS.txt**.
