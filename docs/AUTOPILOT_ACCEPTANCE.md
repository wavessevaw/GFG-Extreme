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

Status: READY FOR DEVICE VALIDATION. Hardware and GPU-clock actuation remain NOT_TESTED. Do not enable clock writes on the Deck yet.
