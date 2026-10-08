# GFG Extreme 1.4.3 — Battery Savings Effort

This release replaces the hours-based **Playtime Target** control with a Battery-only **Savings Effort** selector: **Off · Light · Medium · Hard**.

## Changes

- **Playable frames first.** The old attempt to meet an arbitrary 2/3/4/5-hour deadline could lower TDP to 6 W and leave a heavy game at around 10 real FPS and 30 interpolated FPS. Savings Effort now has conservative power-search floors and an evidence-based rescue: sustained collapse in the **real/source** frame rate can lift the economy ceiling instead of presenting generated output as smooth gameplay.
- **Off / Light / Medium / Hard.** Off adds no power ceiling to the normal Battery Governor. Light has a 14 W economy ceiling, Medium 12 W and Hard 11 W, all subject to real-FPS rescue. These are **soft budgets**, never a guaranteed runtime or FPS.
- **Hard-only panel refresh.** In Battery + Hard on the built-in Steam Deck panel, GFG requests **60 Hz on OLED** or **45 Hz on LCD**, but only if Gamescope reports the exact supported rate. Other Battery levels retain the current panel refresh; Balanced/Quality are not affected. Docked/external displays are not changed.
- **Screen-state restoration.** Before changing refresh, GFG records the original mode and verifies the modeset. Leaving Hard, turning the Governor off, or unloading attempts to restore it. An explicit manual Steam slider change wins.
- **Updated Decky UI, bilingual README, plugin listing and screenshots/illustration**, plus tests for source-FPS regression, mode isolation, Gamescope refresh selection, restoration and manual overrides.
- **Legacy hours requests explicitly fail** instead of silently applying an obsolete power budget. Saved fixed-hour targets are ignored.

## Notes

The Battery savings limits are an initial policy, not a guarantee that a specific game remains playable. Source-FPS protection requires fresh renderer evidence. The actual 60/45 Hz modeset is conditional on hardware capabilities. The renderer and Frame OS functionality are unchanged.

Use the included log recorder if an unexpectedly low real FPS, a failed modeset, or a missed refresh restoration occurs.
