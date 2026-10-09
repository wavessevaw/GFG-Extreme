# GFG Extreme 1.6.10 — GFG Open GPU-cost experiment and device-aware Extreme power

Release status: pre-release

> **TEST BUILD — EXPERIMENTAL.** GFG Open and Extreme are under development. No proof of 90 *unique displayed* FPS on Steam Deck has yet been established. A high reported output FPS may look like 30 real FPS when interpolation falls back.

### Findings from 2026-10-09 Deck log

- 30 real FPS, around 90 nominal output FPS in active generation windows, and 28/143 fixed-plan windows with no generated frames.
- Native GFG Open ended in `passthrough=true` after four failed GPU recovery probes and zero recoveries. The final ~0.24 ms was cheap fallback work, not the original optical-flow cost.
- One generated-image acquire timeout and substantial acquire backpressure were recorded. The pinned MAKO ordered SDR path **already uses Vulkan FIFO**. This release does not force VSync or change present modes.

### Changes

- **Experimental faster color flow:** original nine-sample coarse matching retained for accuracy, 5×5 instead of 7×7 near-seed refinement, and sparser wide matching, to reduce GPU expense. Full-resolution source/output preserved.
- **Honest GPU costs:** persistent full-compute and failed-recovery-probe timings in `open-performance/*.json`. Cheap passthrough samples no longer obscure why recovery failed.
- **Extreme power:** removes global 15 W limit. Upper power bound follows inherited player fast/slow PPT and hardware-reported maxima (15, 20 or higher where supported). Power writes remain bounded and restores remain ownership-aware.
- **CI:** candidate archive version is derived from `package.json`.

### Validation

CI compiles shaders, executes Vulkan image tests on lavapipe in both tile test modes, and validates the real Decky ZIP before publication. Native Deck frame pacing, image quality and GPU cost still require device retesting. No guaranteed FPS improvements are claimed.

Install **GFG-Extreme-v1_6_10.zip** using Decky Loader → Install from zip, and restart the game.

SHA-256: `<sha256>` (also in SHA256SUMS.txt).
