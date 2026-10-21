## GFG Extreme 1.2.3

**Official release** (not pre-release). Stability and diagnostics update for GFG Extreme on Steam Deck.

### In-game Rings and FPS
- Rings stay enabled by default in the **bottom-left corner** on new profiles. Existing choices, including explicit Off, are preserved.
- Rings refresh every **one second**, using fresh renderer telemetry. Invalid or stale measurements are shown as unavailable rather than as invented FPS values.
- **HUD-only mode fixed:** FPS and real FPS now update even when the Governor is disabled. Game launch and display refresh are still detected, without taking TDP control or changing renderer settings.
- Native Vulkan Rings and classic text fallback retain their existing no-stall rendering behavior.

### MotionBoost status
- With experimental Frame OS Act enabled, **Standard** and Detailed Rings now show the MotionBoost state.
- **BOOST 45R x2**, or the corresponding measured values, appears only when the adaptive executor is enabled, the pacer acknowledged the policy, and fresh renderer data confirms higher real-frame cadence with acceptable output FPS.
- **VERIFYING** means MotionBoost was requested but not yet confirmed. **CALM** and **REST** show the current actively applied Frame OS control state. When the executor is inactive, an unverified BOOST claim is never displayed.
- The displayed real/generated ratio is derived from observed output FPS divided by real FPS; it is *not* independently proven per-frame generator provenance, nor a measurement of input-to-photon latency.

### Governor and Frame OS safety
- Expired Steam-focus events no longer leave Governor indefinitely **PAUSED** after returning from Steam UI.
- The same freshness rule now also governs MotionBoost starvation protection, so an old focus-loss flag cannot indefinitely suppress rollback on low output FPS.
- Fresh Steam UI events still pause measurements as designed. Focus handling uses one consistent monotonic clock.
- New automated regressions cover Governor Off + Rings On, real-frame boost verification, missing acknowledgements, stale telemetry, Steam focus expiration and starvation fallback.

### Measurements and scope
The Energy ring reports the difference between configured TDP ceilings, **not measured battery-energy savings**. The Frame OS Response estimate is not a measured input-to-photon-latency improvement. Real Steam Deck A/B validation remains necessary for performance or battery claims.

### Install
Install `GFG-Extreme-v1_2_3.zip` from GitHub Releases using Decky Loader **Install from zip**. Restart games already running so the updated native Vulkan HUD layer can load.

### Verify your download
SHA-256: `<sha256>` (also provided in `SHA256SUMS.txt`).
