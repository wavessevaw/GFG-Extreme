# Autopilot 2.0.1 acceptance

Branch: `feature/autopilot-2.0.0`
PR: #117
Previous package: `v2.0.0` at `0e770b8` (superseded; do not use it for this fix)

| Criterion | Result | Evidence | Limit |
| --- | --- | --- | --- |
| Autopilot goal reaches Governor | PASS | `GoalAndPauseTests.test_a_sustained_miss_becomes_the_governor_target`. ` _governor_target` replaces `target_for` before the budget step. A held 90 moves to 60 only after three fresh misses, then back after three good windows. | Display refresh is not changed. |
| FRAME ring | PASS | `FrameToneTests`: 45×2 at 22 ms and 30×3 at 33 ms are green. Jitter warns. An unconfirmed multiplier is grey. A doubled real interval is red. | On-screen placement NOT_TESTED. |
| HUD session clears on Stop | PASS | `test_stop_clears_the_autopilot_hud_session`. The ring payload is active only when the Governor is enabled, the mode is autopilot, and the session is active. | Device screenshot NOT_TESTED. |
| Post-change measurements | PASS | `test_a_clock_check_asks_for_samples_after_the_change` records `summary(..., after_seq=baseline)`. Judge refuses a window under 5 samples or 2 seconds. | Hardware clock writes BLOCKED. |
| PAUSE and HOLD | PASS | `test_pause_blocks_a_planned_power_probe`: plan is `pause`, a healthy budget window returns `hold`, and planned Flow/CPU admission is blocked. | Protective unhealthy path remains in BudgetController. |
| GPU clock writes | BLOCKED | Service constructs `GpuClock(writes_enabled=False)`. | Deck restore NOT_TESTED. |
| Restore lock | PASS | Unconfirmed restore stays `RESTORE_PENDING` and rejects a new clock experiment. | Live amdgpu NOT_TESTED. |
| Regression | PASS | Local discover: 1030 tests. Two `os.chown(65534)` errors are this sandbox. GitHub CI is the confirmation. | |
| CI / ZIP | PASS | Code `6765fecffd621876ceb78046390e118299739581`. CI push https://github.com/wavessevaw/GFG-Extreme/actions/runs/38061085826. CI PR https://github.com/wavessevaw/GFG-Extreme/actions/runs/38061088788. Release https://github.com/wavessevaw/GFG-Extreme/actions/runs/38061085831. Zip `GFG-Extreme-v2_0_1.zip`, sha256 `c2ee5d95db7bf27315ba39e3f98103bb1ce7ffe588447c737cdd2aa73cb0a7a5`. Prerelease, not latest. `v2.0.0` is the older package. | |

## Independent code-review corrections

Verified source commit: `275760e209ba3e1057dfb961586e9b1dad06f05a` (subsequent documentation-only commits do not change runtime).

| Finding | Correction | Regression evidence |
| --- | --- | --- |
| Smoothness confused real-frame time with generated output budget | `autopilot/planner.py` evaluates real-frame time against verified real-cadence goal (or real median when multiplier unknown) | `ColorAndModeRegressionTests.test_smoothness_compares_real_frametime_with_real_cadence` |
| 90→60 transitions counted the same sliding FPS window multiple times, and 60 could get stuck | `TargetPolicy` requires disjoint, sequenced windows; cautious 90 Hz recovery probe after 90 seconds and longer 240-second backoff after failed retry | `HoldAndTargetTests.test_the_display_target_does_not_flap`, `GoalAndPauseTests.test_a_sustained_miss_becomes_the_governor_target` |
| Autopilot HOLD could freeze Flow in Quality or Balanced | Mode-owned plan lock; clear Autopilot plan, controller probe flags and HUD state on active profile mode change or Stop | `ColorAndModeRegressionTests.test_mode_switch_releases_the_autopilot_plan_lock` |
| Battery and TDP rings showed green despite low battery, missing cap or power-control error | Battery thresholds, low-runtime warning, observed TDP/error/override color semantics | `ColorAndModeRegressionTests.test_battery_and_power_tones_are_not_always_green` |
| Old green metrics remained visible on stale FPS samples | Renderer-dependent ring tones forced gray when telemetry snapshot is stale | `governor_service.py::_publish_ring_hud_locked` |

CI on source commit: https://github.com/wavessevaw/GFG-Extreme/actions/runs/38062335037 , completed successfully, 1033 Python tests (one skipped) and frontend smoke. Hardware verification: NOT_TESTED. The published `v2.0.1` ZIP still targets `6765fec` and **does not contain these follow-up fixes**; build a new pre-release from the corrected source before distributing it.

**Remaining hardware concerns:** verify the behavior of a 60 FPS output goal on a physical 90 Hz OLED display (mixed cadence may stutter); GPU Clock real writes are disabled and remain NOT_VERIFIED on device.

Status: READY FOR CONTROLLED DEVICE VALIDATION (source only; refreshed installable package required). Hardware and GPU-clock actuation remain NOT_TESTED. Do not enable clock writes on the Deck yet.



## Autopilot 2.0.2 experimental release gate

This supersedes the old 2.0.1 rows above specifically for the two new, explicitly
requested resource actuators. Do not report the old 2.0.1 release ZIP as
containing the new code.

| Feature | Software status | Hardware status |
| --- | --- | --- |
| GPU Clock SteamOSManager (QAM) | Implemented using session D-Bus `GpuPerformanceLevel1` with `steamosctl` fallback; mock property read/write, previous manual value + Auto restore, external manual override, missing-interface fallback exercised by `tests/test_steamos_gpu.py`. | **NOT TESTED on Deck**. Underlying SteamOSManager presence and safe manual clock behavior vary by firmware. |
| Half Rate Shading | Steam `RADV_FORCE_VRS_CONFIG_FILE` live 1x1/2x2 integration; explicit per-profile opt-in, single arbiter, rollback, receipt-based recovery, `tests/test_half_rate_autopilot.py`. | **NOT TESTED on Deck**. RADV/VRS game compatibility and legibility must be evaluated visually; FPS readings alone cannot measure image-quality loss. |
| CPU/GPU/FPS/temp/power efficiency | Existing Linux CPU/GPU sensor sampler and Governor renderer FPS/frametime samples linked to decisions, thermal and watt readings logged. | Values sourced from system/renderer telemetry; this does **not** scrape pixels of the Steam Performance Overlay. |
| Other Steam QAM controls | Allow Tearing remains untouched. | No automatic control or hardware testing. |
| Release | Version 2.0.2 with `gfgPrerelease` true. Publish only after all CI, native, frontend and packaging checks succeed, and include exact release SHA and SHA-256. | Device validation is separate from successful CI. |

**Status:** experimental software implementation; hardware ready-for-testing is not
a claim of measured performance, restore reliability or visual correctness.
