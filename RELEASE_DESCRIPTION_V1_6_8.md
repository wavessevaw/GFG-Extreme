# GFG Extreme 1.6.8

Official release of the ordinary GFG renderer. Restart running games after upgrading.

## Keep optimization accountable to delivered frames
- Accepted automatic flow-scale choices continue to monitor fresh cadence. A severe shortfall restores the player's Saved flow value immediately; two consecutive moderate shortfalls also restore it. Missing or changed applied flow state removes the success claim and triggers an acknowledged rollback. Failed choices are not retried in the same context.
- Incomplete frame-generation state supersedes an earlier flow acknowledgement. An old successful value can no longer stand in for a newer missing value or unavailable resources.
- Spatial-layer diagnostics no longer replace frame-generation capacity or game FPS. This keeps unrelated zero-slot reports from disabling the ordinary generator or blocking Extreme's deeper ratios.
- Measured zero output, when real cadence is available, stays zero instead of becoming a theoretical 90 FPS from the planned multiplier. Plan-only samples cannot prove a flow benefit and do not populate the Rings HUD's live FPS counter.

## Existing controls and release packaging
Extreme retains the quarter-step ratios through 4x, subject to actual renderer capacity and cadence checks. Battery, Balanced and Quality keep their separate optimization goals. Saved profiles, the generator model and the inherited power ceiling are unchanged.

ENERGY retains saved TDP allowance in its centre and battery charge in its arc. TDP remains green on external power and changes with battery charge when unplugged. The theme installer remains available in Settings.

The startup log now identifies the installed version correctly. Repeated builds can reuse a cached previous-release archive instead of downloading it again; archive checksums and ZIP CRC are still verified on every build. Initial cache misses still count as GitHub asset downloads.

## Extreme ceiling and HUD rate
- While Extreme stays enabled, a new game session, a missing overlay or a gap in FPS telemetry keeps both PPT channels at the clamped ceiling. Those paths used to restore the higher inherited fastPPT for one Governor tick. Turning Extreme off, changing profile or any real exit still restores the original caps.
- A failed power claim outside Extreme is no longer labelled `extreme-ceiling-not-applied`.
- The in-game HUD is published twice a second, the same rate the Vulkan layer already polls. Governor power decisions stay once a second. The MangoHud config file is still rewritten at most once every 5 seconds.

## Validation and limits
Backend regression tests cover held-flow starvation, duplicate samples, healthy recovery, unexpected and incomplete acknowledgements, role isolation, measured zero output, plan-only HUD data, real overlay rollback, Extreme ceiling handoff and the half-second HUD publish. Native Frame OS/HUD integration, HUD pixels, frontend smoke cases and the final Decky archive are checked before publication.

Extreme, Frame OS Act and automatic flow tuning remain experimental features inside an official release. GFG Open remains retired. These fixes prevent invalid optimization and misleading evidence; they do not claim a measured on-device FPS, latency or ghosting improvement.
