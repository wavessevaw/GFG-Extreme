## GFG Extreme 1.6.5: bounded transitions and reversible runtime foundations

### Changes
- Extreme claims power with both fastPPT and slowPPT already bounded by the stock 15 W ceiling or a lower inherited user limit. Renderer trials stop if applying the ceiling fails.
- Internal mode/display replanning keeps the Extreme ceiling instead of temporarily restoring a previous 20 W cap. Leaving Extreme restores inherited settings.
- Successful ceiling retries resume the search; an old failure status no longer blocks recovery.
- Rejected operating points record fresh requested and delivered real/output FPS, multiplier, renderer acknowledgement, sample count and observation span. A reused telemetry session cannot supply evidence for the request.
- Native Frame OS gains an optional stall-shield policy and explicit support/active telemetry, preserving the existing behavior when the policy is off.
- The privileged helper gains bounded leases and persistent undo for GFG-marked game thread priority, OOM preference and OEM fan-controller selection. PID/TID identity checks, readback, EOF/expiry recovery and external-change preservation are covered by regression tests.
- Updated launch wrappers identify GFG-managed games for scoped resource control.

### Current scope
The resource primitives and optional shield are foundations for the remaining booster integration; they are not automatically activated or represented as completed boosters. OOM preference is not swap/huge-page tuning. OEM controller selection is not predictive cooling.

This release does not claim a fix for Ghost of Tsushima ignoring render scaling, all fractional-point failures, Act starvation or ghosting. `delivered-deeper-ratio` can mean the renderer maintains target output using fewer real frames; the new evidence makes that distinction inspectable.

### Validation
GitHub Actions checks backend regressions, native Frame OS/HUD tests and ABI, frontend build/smoke tests, HUD cost and release packaging. Device-level FPS gain, controller behavior, input latency and image quality still require a physical Deck comparison.

### Install
Download **GFG-Extreme-v1_6_5.zip** and install through Decky Loader (Install from zip). Relaunch the game to use the updated launcher and native layers.

SHA-256: `<sha256>` (also in SHA256SUMS.txt).
