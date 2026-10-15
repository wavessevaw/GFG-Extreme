# GFG Extreme 2.1.2-te.7 — Temporal Engine beta with GFG Shell (pre-release)

**Experimental build for hardware trials.** Everything else is GFG Extreme 2.1.1.

te.7 reworks the parts of the LMC frame generator that were slow on the Steam Deck's GPU, and replaces the generator's pauses with cheaper quality tiers.

**The motion model is fitted on the CPU.** The camera planes and the motion palette were fitted on the GPU by passes that ran on a single workgroup, the slowest part of the analysis on a GPU shared with the game. They are now fitted on the CPU, on a worker thread (about 2 ms on a desktop CPU; the Deck's time is in the renderer log). The analysis is two submissions: the first finds the block vectors, the CPU fits the model of that same pair, then the second builds the per-pixel fields. The engine has its own Vulkan queue, so only the engine waits for the fit, never the game. The renderer log reports the wait as `fit_wait` and leaves it out of the GPU time.

**Coalesced passes.** The block statistics, the quarter-resolution masked luma and the orphan count looped over a block's pixels in one thread, so neighbouring threads read memory far apart. They now use one thread per pixel and a reduction in workgroup memory (8–32 registers, no spills on RDNA2).

**Fewer dispatches in the block search.** Each pyramid level ran 7 dispatches, each followed by a barrier; it now runs 4, which ping-pong between two buffers instead of copying.

**Cheaper tiers instead of pauses.** When the generator stayed over its GPU budget, it stopped generating for 120 frame pairs and repeated real frames, which you see as stutter. Now it first moves to cheaper tiers:
- Tier 1 carries the second motion grid from the first instead of searching it again.
- Tier 2 also runs one propagation sweep instead of two.

It pauses only when tier 2 is still over budget, and moves back up when the cost allows. The renderer log reports `tier=` and `tier_steps=`.

**Picture.** On the seven rendered bench scenes the full tier matches te.6 (FLIP within 0.5 % on every scene). Tier 1 has the same mean and up to 6 % worse worst frames (the specular scene). Tier 2 is up to 1 % worse on average and up to 16 % worse in its worst frames. Both are far better than repeated frames.

**GPU cost on the Deck.** Not measured yet, so this build gives no estimate. Every 10 seconds the renderer log records the GPU time of each analysis pass, the CPU fit wait and the tier; one trial log is enough to measure it.

**GFG Shell 0.3.0 is included.** The alternative Gaming Mode shell (Godot; Steam stays the game client) has a new look:
- Portrait game capsules.
- The selected game's art behind the page, with a slow drift and a cross-fade.
- Focus lift with a glow.
- Sliding menus with shadows.
- A Store page with direct links to the store, specials, wishlist and key activation.

Install and launch it from the plugin: **GFG Extreme → GFG Shell → Install**, then **Launch**.

How to test: install **GFG-Extreme-v2_1_2-te_7.zip** through Decky, **Settings → System → Update engine**, restart the game through `/home/deck/.local/bin/gfg %command%`, keep **Temporal Engine · Experimental**, record a log of 2–3 minutes of play with camera movement, then the same with Temporal Engine **Off**.

SHA-256: `<sha256>` — also see **SHA256SUMS.txt**.
