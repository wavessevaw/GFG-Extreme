# GFG Extreme 1.6.9

Official release of the ordinary GFG renderer. Restart running games after upgrading.

## Decisions use delivered frames
- A diagnostics line that only carries a planned multiplier is no longer a frame the Governor can act on. Power steps, the guard, Act's starvation check and the session average ignore it. Measured output, including a measured zero, and scheduler-interval samples still count.
- The text HUD no longer prints that planned rate as FPS. The ring HUD already refused it.
- A rejected operating point in a session report now shows the measured output and real cadence next to what was requested, when that evidence exists. A planned multiplier is not described as delivery.

## Unchanged
Extreme still clamps both PPT channels to the inherited ceiling and keeps that clamp across a new session, a missing overlay and a telemetry gap. The HUD still publishes twice a second. Flow trials, Battery, Balanced and Quality keep their existing goals. Saved profiles and the generator model are unchanged.

## Validation and limits
Backend regression tests cover a plan-only window, a mixed window, the text HUD and the rejection report. Native Frame OS/HUD integration, HUD pixels, frontend smoke cases and the final Decky archive are checked before publication.

Extreme, Frame OS Act and automatic flow tuning remain experimental features inside an official release. GFG Open remains retired. This release stops planned FPS from steering power; it does not claim a measured on-device FPS, latency or ghosting improvement.
