# GFG Extreme 2.0.1

Official maintenance release for Autopilot and Frame OS control paths.

## Fixes

- GPU Clock and opted-in Half Rate Shading can now be proposed on stable, heavily loaded game cadence. Previously they were proposed only below the FPS goal, while admission required at least 95% of the goal: every shading request in the supplied 2.0.0 extract was skipped. Confirmation, clean baseline and Steam-menu guards remain required.
- SteamOSManager's manual GPU clock step starts below the observed GPU MHz, rather than below the hardware maximum, so the proposed downward step cannot accidentally pin a lightly loaded GPU at a higher frequency.
- GPU/VRS verification times out on repeated or stale samples, checks heat immediately, and requires post-change windows. The core loop reaches this timeout even when the renderer becomes silent.
- Pending GPU/VRS restoration blocks new resource control across Battery, Balanced, Quality and Autopilot. An idle GPU restore cannot clear a shading restore lock. Plugin restart restores an unjudged clock trial; QAM overrides remain respected during retry and while holding a verified clock.
- Skipped/rejected actuator trials leave the ordinary power Governor available. Failed writes back off; the HUD does not announce an experiment after it has ended.
- Steam menu samples, resumed pre-transition windows and stale telemetry cannot lower the Autopilot FPS goal.
- Repeated short Frame OS boosts that never show increased real cadence now accumulate failure exposure after the interval-ring settle period. Backoff releases the adaptive executor point to Governor rather than holding it indefinitely. Missing cadence alone is not learned as failure.
- Point release restores GFG-owned GPU/VRS settings before returning to the base rendering point.

## Evidence and validation

Audited `diagnostics/autopilot-2.0.0-20261011-230354`, commit `c3bd63e`: 2,184 session samples over 2,206 seconds, median 29.999 real / 89.993 output FPS, and 15 verbatim skipped-shading events. The extract reports unchanged 30 real FPS in boost and calm. All 15 shading events are preserved in a regression fixture. See `docs/RELEASE_AUDIT_2_0_1.md` for evidence boundaries and test coverage.

Backend, native Vulkan mock-driver/HUD tests, frontend build/smoke and Decky archive integrity/version checks must succeed before this workflow publishes the ZIP.

## Limits

The diagnostics branch contains a summary and skipped events, not the full raw recording. These fixes are software-validated; GPU/VRS behavior and performance gains in 2.0.1 still require a physical Steam Deck test. No increase in unique display frames, input-to-photon latency or battery life is claimed. The upstream bundled renderer is unchanged; generated-image acquisition timeouts are not claimed resolved. The logged game overrides render extent, so render-scale reductions cannot make that game render at a lower resolution. Half Rate Shading stays opt-in and can reduce clarity. Display refresh and Allow Tearing are not changed by these fixes.

Installation: Decky Loader -> Install from zip -> `GFG-Extreme-v2_0_1.zip`, then restart the game.

SHA-256: `<sha256>` (also in `SHA256SUMS.txt`).
