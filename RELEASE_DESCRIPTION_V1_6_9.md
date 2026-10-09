# GFG Extreme 1.6.9 — GFG Open guarded recovery (experimental)

Release status: pre-release

> **TEST BUILD — NOT RECOMMENDED FOR REGULAR PLAY.** GFG Open and Extreme remain experimental. High reported output FPS can coexist with low effective motion smoothness. Do not infer 90 unique displayed frames from a 90 FPS counter.

After a real-world 1.6.7 Deck session reported 90 output FPS while feeling like 30–40 FPS, diagnostics revealed 30 real FPS, GFG Open stuck in `passthrough=true`, and occasional generated-image acquire timeouts. This update addresses the independently verified permanent-pass-through mechanism, **not** a proven FIFO defect.

- **Guarded GPU recovery:** after 300 real-frame pairs in fallback, sample actual interpolation work. Three consecutive genuine GPU samples <=3 ms restore generation; failed probes return to pass-through with capped exponential backoff (600, 1200, 1800 source pairs). Cheap passthrough measurements never count as evidence of recovery.
- **Fail-closed behaviour:** GPU timestamp-unavailable contexts stay in passthrough. Sustained expensive synthesis stays protected; no blind forced re-enable.
- **Safety diagnostics:** open-performance JSON now includes `safety_latched`, `recovery_probe`, `probe_attempts`, `recoveries`, `next_probe_frames`, `interpolation_attempted` and current `passthrough`. Recovery transitions log explicitly.
- **History prepass:** respects the bypass state rather than always dispatching the full history prepass.
- **Tests:** deterministic cooldown, successful recovery, failure backoff, non-timing, and persistent fallback cases.

**Not claimed:** FIFO/presentation changes, an on-device smoothness fix, or proven battery/FPS gains. The session's generated-image timeouts are transport/acquire events outside GFG Open compute and require separate instrumentation and Deck retesting. The MAKO transport is pinned; it is not safe to replace its present mode without evidence.

Install **GFG-Extreme-v1_6_9.zip** with Decky Loader → Install from zip, and restart the game. GFG Open remains native x86_64 SDR8 opt-in; Flatpak uses legacy generation.

SHA-256: `<sha256>` (also in SHA256SUMS.txt).
