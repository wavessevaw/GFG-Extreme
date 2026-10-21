# GFG Extreme 2.1.4 — Governor target stability and Frame OS power ownership

## Fixes
- Autopilot no longer silently downgrades a 90 Hz display goal to 45 FPS when real FPS briefly drops below 28. The explicitly selected Battery preference retains its deliberate 45 FPS fallback.
- Frame OS Act no longer applies short-lived boost/rest offsets directly to the hardware TDP limit. The Governor remains the single owner of the hardware power budget, avoiding competing 11–15 W writes observed in 2.1.3 field logs.
- Regression coverage for the display-goal policy and Frame OS Act power arbitration.

## Notes
- Frame OS Act pacing remains available; the per-frame hardware-TDP boost/rest overlay is disabled to preserve stable measurements.
- Steam Deck long-session hardware validation is still recommended, particularly for thermals, latency and energy efficiency.
