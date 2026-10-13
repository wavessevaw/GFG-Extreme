# GFG Extreme 2.0.2

Official mode-objective update for Battery, Balanced and Quality.

- Battery now targets the lowest verified feasible TDP, rather than keeping a fixed 6 W comfort floor when the device reports a lower minimum. After finding a floor for the current real cadence, it may confirm a cheaper compatible normal cadence/scale and resume searching down. Failed trials restore the known-good point and watts; unavailable ratios and ignored power caps cannot claim savings. Autopilot's Battery preference uses the same minimum-power goal.
- Balanced keeps its 30-real-FPS floor and normal power ceiling, and can retest a finer frame ratio when power cannot be reduced further. Heat and rejection cooldowns block these trials.
- Quality now preserves saved render resolution in both recommendations and the actual trial ladder. After five minutes of clean play, it can trial a finer ratio at the saved power budget, with the previous point retained for rollback. Failed points cool down for ten minutes instead of remaining rejected forever within the same session.
- The interface describes Battery's minimum-power goal and Quality's resolution/recovery behavior.

Sixteen focused objective tests accompany the existing mode, telemetry, restoration, replay, native Vulkan/HUD and frontend tests. See `docs/MODE_OBJECTIVES.md`. The release workflow repeats software checks and validates the Decky archive before publishing.

Model-based test examples (7 W versus 6 W, or 3 W on a sufficiently light scene) are not measured improvements on a physical Steam Deck. Actual minimum power depends on the game, target cadence, renderer capacity and hardware. A failed hardware-minimum probe returns to the proven feasible value. The bundled upstream renderer is unchanged.

Install using Decky Loader -> Install from zip -> `GFG-Extreme-v2_0_2.zip`, then restart the game.

SHA-256: `<sha256>` (also in `SHA256SUMS.txt`).
