# GFG Extreme 2.1.3 — Governor recovery and HUD cadence

Bug-fix release focused on Governor behavior during workload changes.

## Governor
- Recover toward a previously proven, binding TDP when active gameplay resumes after an economy reduction, instead of immediately interpreting the temporary FPS collapse as proof that the display goal should fall from 90 to 45 FPS.
- Keep the 90 FPS goal while known-good TDP recovery is possible. Recovery respects device/user limits and is only based on fresh telemetry.
- Classify deep collapses during frame generation where output falls back to real FPS as loading/location-transition stalls. These intervals no longer count as ordinary power-capacity failures or trigger the normal starvation response.
- Keep normal evaluation active after fresh gameplay telemetry returns; transient protection is not a permanent lock.

## HUD
- Preserve the 500 ms HUD heartbeat independently from the Governor's one-second power-decision cadence.
- Prevent frequent UI/config wakeups from indefinitely skipping HUD updates.
- Avoid additional MangoHud config rewrites when content has not changed.

## Validation
Automated regression tests cover known-good TDP recovery, loading-transition classification, Autopilot goal retention and HUD cadence under frequent wakeups. CI results are reported separately from Steam Deck hardware validation.

This release does not claim that the changes have been verified in a real Steam Deck game session until hardware testing is completed.

Install **GFG-Extreme-v2_1_3.zip** through Decky's Install from zip.

SHA-256: `<sha256>` — also see **SHA256SUMS.txt**.
