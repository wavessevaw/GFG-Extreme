# GFG Extreme 2.0.0 | Autopilot

**Official release** • 11 October 2026

Autopilot replaces the former Extreme mode. An existing Extreme profile is migrated without overwriting its Saved rendering settings. The normal Governor remains the sole TDP controller.

## Main functionality

- Real/output FPS targets based on renderer evidence; automatic 90/60 goal selection when measured cadence cannot maintain the panel goal.
- Governor adjusts the verified TDP limit. Failed lower-watt experiments roll back and are remembered; repeat failures now back off for up to 30 minutes (including across restarts).
- SteamOSManager GPU Clock trials are restricted to likely CPU bottlenecks and respect Steam QAM manual overrides, with verified readback and rollback. Unsupported devices fail closed.
- Opt-in Half Rate Shading (RADV VRS 2x2) experiments have exclusive ownership, verification and restore. They are not attempted while the Steam Quick Access Menu is open or before a stable, confirmed operating point and fresh evidence.
- Autopilot's HUD uses measured real/output FPS, GPU and CPU activity, temperature, frametime and APU watts. Deferred, blocked and failed experiments are now reported as skipped or paused, never as successfully applied.
- Stop, game exit and mode changes restore GFG-owned GPU/VRS settings or retain a retryable restore-pending lock.

## Fixes verified from the 11 October field log

- Lower watt failures such as the repeatedly unsuccessful 9 W trials no longer trigger frequent repeated dips without a significant new opportunity.
- UI no longer states that GPU Clock or Half Rate Shading is being tested if the experiment has not started.
- Plugin, Governor and diagnostic exporter now all identify this build as **2.0.0** rather than mixing 2.0.1 and 2.0.4.
- The Steam QAM transition can no longer be mistaken for a clean performance comparison.

## Validation and limitations

Automated backend tests, native Frame OS/HUD Vulkan mock-driver tests, frontend smoke tests and Decky archive integrity checks run in CI before publication. No gain in unique display frames, input latency, image quality or battery life is claimed from the available session.

**GPU-clock writes and dynamic Half Rate Shading have not yet been validated on a physical Steam Deck LCD/OLED in this release.** The opt-in shading feature may reduce text/HUD clarity. The renderer's occasional generated-image acquisition timeouts and Frame OS Act responsiveness have not been proven resolved by this update. Allow Tearing is not changed automatically.

Installation: Decky Loader → Install from zip → `GFG-Extreme-v2_0_0.zip`, then restart the game.

SHA-256: `<sha256>` (also in SHA256SUMS.txt).
