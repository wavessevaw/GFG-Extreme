# GFG Extreme 1.6.7 — GPU work limits and power accounting

Release status: pre-release

> **IN DEVELOPMENT — NOT RECOMMENDED FOR REGULAR PLAY.** GFG Open remains experimental and may reduce real FPS or introduce image artifacts. Use this build for testing; leave GFG Open disabled for regular play. Field recovery has not yet been verified on Steam Deck.

This update addresses risks exposed by the first GFG Open field recording. That recording used Witcher 3 in Battery mode and showed a substantial real-FPS shortfall. It did not isolate shader cost from pacing or other effects.

- **Late-frame pacing:** Frame OS no longer rounds a late real frame up to the next whole slot. Previously 34 ms of work under a 30 Hz policy could be paced at 66.67 ms (15 FPS). Ready late frames are now released immediately and the schedule is re-anchored, independently of Stall shield.
- **Open GPU workload:** motion matching uses a 16×16 grid (four times fewer tile searches at 1280×800, with source/output resolution preserved); wide refinement uses a bounded two-pixel lattice instead of the previous dense pixel-by-pixel sweep, with at most 36 expensive wide comparisons per tile and a small local polish. Duplicate local candidates are skipped.
- **GPU timing and protection:** native timestamps measure matching and each generated-frame composition. After repeated execution costs above 4 ms, Open switches to real-frame passthrough for that context and logs the reason. This protects the game's render budget; it does not restore legacy interpolation during the same launch. To use legacy FG, turn off GFG Open generator and restart the game.
- **Energy number:** uses the upper bound of SteamOS Manager's Gamescope/QAM TDP slider, with the hardware maximum as fallback. A 15 W cap under a 20 W slider maximum displays **25%**. Existing arcs, colours and layout are preserved. The value is cap savings, not measured battery savings.
- **CPU recovery:** accepted helper writes retain ownership candidates when immediate readback is stale, so a late own cap is not classified as an external writer. Ordered restoration covers all policies; diagnostics expose observed and pending per-policy caps.
- **A/B provenance:** live measured benefits use this session's control pairs; earlier-session values stay in historical diagnostics.

GFG Open remains experimental and opt-in. Native x86_64 SDR is supported; Flatpak uses the existing generator. This release does not claim that a twofold field regression is fully resolved without a comparable device retest. Vulkan image tests establish functional behaviour, not Steam Deck performance or end-to-end latency.

Install **GFG-Extreme-v1_6_7.zip** through Decky Loader → Install from zip, then restart the game.

SHA-256: `<sha256>` (also in SHA256SUMS.txt).
