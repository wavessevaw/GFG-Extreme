# GFG Extreme 2.1.6: Integrated Governor, Fusion, Power Split and Frame OS Reliability Release

## Fixed
**Frame Fusion activation (PR #140).** The Governor could enable Fusion, but manually serialized TOML omitted `gfg_frame_fusion`. MAKO therefore defaulted to `requested=false` / `disabled-at-launch`. The profile now includes the field. Live Autopilot/Fusion toggles are reconciled despite unchanged Saved data and cached point/Act/Flow overlays cannot reintroduce stale consent.

**CPU/GPU Power Split (PR #141).** No CPU cap during Governor TDP/operating-point trials or concurrent GPU Clock/VRS experiments. CPU caps are restored on telemetry loss, overload, manual takeover and exit; hardware ownership and write-ahead recovery are preserved. Each CPU frequency rung must be checked anew. Matching A/B/A windows protect Real FPS and require a statistically supported GPU-headroom improvement before recording the level across sessions. Legacy unverified Power Split memory is invalidated.

**Frame OS A/B, Rest, Boost (PR #142).** Proof requires the pacer to acknowledge the actual applied policy generation and a fresh real-present counter. Rejected/stale control writes produce no A/B gain. APU rest-power comparisons must contain independent slow-sensor readings, not ten repeated reads per second. Pre-fix A/B memory that could disable Shaping/Rest without applied-policy proof is invalidated; malformed NaN/Infinity gains are discarded. Frame OS never applies its notional Boost +4 W or Rest TDP offsets in 2.1.6: Governor is the sole hardware TDP writer. Requested and applied watts are reported separately; energy claims no longer include imaginary offset savings.

**Retained from 2.1.5.** Bounded emergency Real FPS recovery from a prolonged ×4 operating point, Autopilot 90 FPS target policy and single-owner TDP safeguards.

## Verification
Before publication, 2.1.6 must pass full backend/frontend CI, Temporal Engine, Frame Fusion native and ASan/UBSan, the Decky ZIP version/CRC/native-payload integrity tests and SHA256SUMS. Passing tests establishes only software behavior under their conditions.

## Hardware work still open
- Fresh Steam Deck proof is required for Fusion `requested=true` plus successful native transfer counters; a corrected TOML value alone is not a physical performance result.
- Same-resolution 1280x800 source/presentation still prevents spatial Fusion scaling; the game must provide a real extent split.
- Historic generated-delivery misses and acquire quarantines are **not** claimed fixed without device diagnostics.
- CPU/GPU Split battery gain, A/B energy benefit, actual Boost frame delivery, latency and thermal effects require controlled hardware OFF/ON trials with Real FPS, p95/p99 frametimes and draw measurements.
- Independent GSF 30→90 hardware frame generation is **not** claimed shipped. Supported generation setup continues to require Lossless Scaling.
