# GFG Extreme 1.6.11-test.1 — Open intermediate-motion test

> **TEST BUILD — EXPERIMENTAL.** This candidate is for the reported “89–90 output FPS but 30–35 FPS motion” defect. It is not an official stable release. GFG Open and Extreme remain under development.

Original Deck recordings show Open in `passthrough=true`, including four failed recovery probes and no recoveries. The bypass shader copies a real image into generated outputs: submitted output FPS therefore does not prove new intermediate motion. Ordered SDR already uses FIFO; this candidate does not replace presentation modes.

- **Cadence-aware GPU guard:** after five valid source intervals, use one quarter of the median source-frame period, bounded to 2–8 ms for the entire prepass/composition batch. At 30 real FPS this is 8 ms instead of a fixed 4 ms. Recovery requires three actual interpolation samples below 75% of the current allowance. Long menu/stall intervals cannot increase it; unavailable timestamps and sustained overruns still bypass.
- **Less repeated GPU work:** cache each tile's fixed reference patch across all motion candidates. Search range, candidate ordering, wide-search limits, confidence and occlusion rules are retained. Functional image output is compared with the original 1.6.10 SPIR-V.
- **Actual motion regression:** Vulkan tests for ×3 verify that the two intermediate images land at 1/3 and 2/3 of motion, differ from both source images, and differ from one another.
- **Diagnostics:** report the active guard/recovery allowance and separate scheduled interpolation/real-copy counts. These counts describe submitted synthesis work, not independently measured unique display frames.

**Install:** install **GFG-Extreme-v1_6_11-test_1.zip** through Decky Loader, enable GFG Open for the game, and restart the game to load native build `4.0.0-gfg.open.2`. Compare the same moving-camera scene with the ordinary engine. The question is visible smoothness and retained real FPS, not whether the output counter reaches 90.

All automated checks must pass before this test build is published. Physical Steam Deck performance and smoothness remain unverified; official release is pending the user's device test.

SHA-256: `<sha256>` (also in SHA256SUMS.txt).
