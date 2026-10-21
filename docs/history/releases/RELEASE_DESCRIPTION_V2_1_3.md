# GFG Extreme 2.1.3 — Governor recovery and HUD cadence

Bug-fix release focused on Governor behavior during workload changes.

## Governor
- Recover toward a previously proven, binding TDP when active gameplay resumes after an economy reduction, instead of immediately interpreting the temporary FPS collapse as proof that the display goal should fall from 90 to 45 FPS.
- Keep the 90 FPS goal while known-good TDP recovery is possible. Recovery respects device/user limits and is only based on fresh telemetry.
- Classify deep collapses during frame generation where output falls back to real FPS as loading/location-transition stalls. These intervals no longer count as ordinary power-capacity failures or trigger the normal starvation response.
- Keep normal evaluation active after fresh gameplay telemetry returns; transient protection is not a permanent lock.

## Causal memory and recovery safeguards
- Keep working-power memory scoped to the current cadence and render-scale operating point, refreshed during confirmed stable play, with a 15-minute lifetime and a maximum of 128 entries.
- Require two fresh healthy windows after fast or periodic slow power recovery before calling the new level stable or restarting probes. A power request is not a confirmed working point.
- Restore reachable same-context working watts on severe economy failures, including the slow path without a draw sensor. Moderate probe failures return to their exact rollback point to avoid importing a heavy scene's power budget into light play.
- Discard pre-recovery target-downshift evidence and keep the current target consistent between Governor and TargetPolicy. Historical watts above the current ceiling cannot block goal adaptation indefinitely.
- Treat a deeply starved but actively generating stream as gameplay rather than holding it as a loading screen for two minutes.
- Reject invalid power readings as binding evidence, discard old-cap draw after a TDP write and inhibit fast watt increases while the APU is hot.
- Link diagnostic decisions to their requested/applied power and fresh-evidence boundary; recovery status uses the current, unexpired operating-point context.

## HUD
- Preserve the 500 ms HUD heartbeat independently from the Governor's one-second power-decision cadence.
- Prevent frequent UI/config wakeups from indefinitely skipping HUD updates.
- Avoid additional MangoHud config rewrites when content has not changed.

## Validation
Software validation includes 14 targeted causal regressions, 22 deterministic plant scenarios and a passing 1,293-test Backend suite, plus CI frontend/HUD/Frame OS checks, Temporal Engine and Frame Fusion native and ASan/UBSan checks. These are software checks; modeled FPS and power are not Steam Deck measurements.

Historical-log analysis informed the fixes, but the full audit remains open for uninspected binary sources and additional detector classes. This release includes the verified fixes without claiming that every historical source or every possible workload has been exhaustively audited.

This release does not claim that the changes have been verified in a real Steam Deck game session until hardware testing is completed.

Install **GFG-Extreme-v2_1_3.zip** through Decky's Install from zip.

SHA-256: `<sha256>` — also see **SHA256SUMS.txt**.
