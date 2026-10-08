## GFG Extreme 1.2.2

### Faster, lighter Rings HUD
- Rings refresh once a second instead of once every 20 seconds, using recent renderer interval samples.
- Unchanged images skip rasterization, file writes and new texture uploads.
- Rounded backgrounds, ring geometry and decoded glyphs use bounded caches.
- The Vulkan layer no longer waits up to 100 ms for HUD copy fences during presentation. A busy HUD frame is skipped and retried.
- Stale/missing FPS shows as unavailable; zero FPS displays as zero.
- Resize, session changes and failed writes are handled without retaining a stale publication state. Text HUD remains the fallback if a Rings write fails.

### Rings settings and diagnostics
- New installs start with Rings enabled in the bottom-left corner. Existing saved on/off, style and position choices are respected.
- Frame OS Response, Frames and Energy rings are populated after two seconds of live telemetry instead of staying blank for the first minute. No boost yet displays 0% real-frame uplift rather than a missing value; unavailable power or telemetry remains explicitly unavailable.
- The Energy ring represents the change in the configured TDP ceiling, **not measured battery savings**; actual consumption still needs paired Deck trials.
- Fixed the misleading always-REST state: gamepad silence alone cannot verify AFK in games using keyboard/mouse, and stale Steam focus-lost reports expire instead of persisting indefinitely. REST remains available on a fresh Steam UI focus-lost event. Real-world input-mode validation is still pending.
- Existing 1 Hz bitmap refresh remains intact, with caching and fallback to the text overlay.

### Validation
Python regressions cover cadence, caching, stale data, resize, session changes and write failures. A native test checks busy-GPU skip/recovery. CI compares pixels and CPU rasterization time against 1.2.1, alongside the existing Vulkan integration, ABI and frontend checks.

Host measurements do not establish Steam Deck FPS, battery or GPU-driver performance. Frame OS Act and Rings remain experimental; device A/B validation remains pending.

### Install
Install `GFG-Extreme-v1_2_2.zip` through Decky Loader (**Install from zip**). Restart a running game to load the updated native HUD layer.

### Verify your download
SHA-256: `<sha256>` (also in `SHA256SUMS.txt`).
