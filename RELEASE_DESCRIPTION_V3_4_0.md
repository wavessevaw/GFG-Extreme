# GFG Extreme 3.4.0

## New in 3.4.0

GFG Extreme 3.4.0 integrates **GSF Kedavra 1.6.0** while preserving the existing
Autopilot, TDP Governor, Power Split, GPU clock controls, profiles, HUD and diagnostics.

**Graphics → Kedavra Focus** is one on/off switch. It enables adaptive edge
enhancement at a fixed **100% strength**, with no Focus slider. The effect works
live with frame generation on or off. It replaces CAS/DLS while enabled and keeps
their saved settings for when Focus is switched off. Focus is off by default in
existing profiles; game profiles can store their own on/off preference.

Focus is SDR-only; HDR images retain the safe bypass. The existing filter budget
may temporarily bypass filters, including Focus, under sustained GPU pressure;
Quality mode keeps the selected filters. No external upscaler is detected or modified.

Install the full 3.4.0 ZIP, use **Setup → Reinstall Gamescope KEDAVRA**, then reboot.
The package includes its matching 1.6.0 engine/runtime. For rollback, restore system
Gamescope and reboot, then reinstall the previous official 3.3.0 package/runtime.

The Focus candidate was user-tested and approved for this release. No new quantitative
Steam Deck GPU-budget or P95/P99 certification is claimed. Development software-Vulkan
measurements are not hardware measurements. Focus can expose noise or existing FG
artifacts on difficult scenes; switch it off when the source is already too sharp.

[Download 3.4.0](https://github.com/wavessevaw/GFG-Extreme/releases/tag/v3.4.0) ·
[Release notes](RELEASE_DESCRIPTION_V3_4_0.md) ·
[Engine source](https://github.com/wavessevaw/GSF_Kedavra/tree/v1.6.0)


The ZIP retains the complete GFG feature set and includes the updated runtime, benchmark tools and license notices. Verify SHA256SUMS.txt before installing.
