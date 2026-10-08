## GFG Extreme 1.2.1

Fixes from the 1.2.0 release review:

- Holding either stick no longer sends Frame OS into idle/rest after 20 seconds.
- Disconnected input devices are removed and can be rediscovered; lost input clears stale stick activity.
- Frame OS retries failed policy writes and heartbeats.
- Re-enabling Frame OS starts with a fresh energy bank, boost backoff and scene detector.
- Energy-broker ownership follows changes in Governor power control.
- Closing Frame OS releases its control-file mapping and descriptor; failed mappings no longer leak descriptors.
- Release publishing now requires the native pacer/HUD tests, ABI checks and mock Vulkan integration tests. Every new release verifies its Frame OS and HUD ZIP payloads.

### Install
Download `GFG-Extreme-v1_2_1.zip` and install it through Decky Loader (**Install from zip**) over your current version. Settings and profiles are preserved.

Frame OS Act and Rings remain experimental features. Host/CI coverage does not establish Steam Deck frame-ratio, latency or battery improvements. Hardware A/B trials, real GPU/driver validation and Flatpak Frame OS/Rings validation remain pending. Benefit percentages are model/proxy estimates.

### Verify your download
SHA-256 of the zip: `<sha256>` (also in `SHA256SUMS.txt`).
