# GFG Extreme 2.0.3

Fixes control conflicts found in the original Steam Deck log recorded on 2.0.1 at 2026-10-12 00:34:41.

- Autopilot now separates actual renderer/power transitions from ordinary consumed Budget windows. Healthy eight-second baselines can reach opted-in Half Rate Shading and GPU clock trials; real settings changes, Steam menus, stale telemetry and concurrent resource experiments still block admission.
- Output-goal decisions use independent evidence windows. Collecting the next window no longer erases preceding misses. Sustained shortfall can trigger the existing achievable-goal policy, and display changes remain honored during collection.
- Emergency TDP increases remain temporary. Once safe measurements permit a power search, Auto's ordinary HOLD and new clock/shading trials cannot freeze emergency watts. Lower-cap failures restore the confirmed working setting.
- Frame OS Act cannot take or keep the adaptive overlay at an emergency cap in the economy modes. Normal Act yields for power research every five minutes instead of ten. Extreme continues to honor the user's performance ceiling.
- An explicit game override of render resolution is recognized before requesting scaled points. The refusal is remembered for that game; resetting learned data allows a new trial without immediately replaying the old refusal.

Fourteen focused regressions accompany the existing software checks, including actual loop execution, actuator admission, TDP rollback, display/menu protection and scaling refusal. The release workflow runs backend, native Vulkan/HUD and frontend checks and verifies the Decky archive before publishing.

The source recording tested Balanced and Autopilot Auto on 2.0.1, not Battery or Quality on 2.0.2. These fixes retain the 2.0.2 mode objectives. They do not promise a specific minimum wattage or measured battery/FPS gains. The upstream renderer is unchanged; a game that ignores spatial scaling is not forced into an unsupported resolution.

Install using Decky Loader -> Install from zip -> `GFG-Extreme-v2_0_3.zip`, then restart the game.

SHA-256: `<sha256>` (also in `SHA256SUMS.txt`).
