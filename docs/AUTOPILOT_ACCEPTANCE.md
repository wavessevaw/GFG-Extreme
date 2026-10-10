# Autopilot 2.0.0 acceptance

Branch: `feature/autopilot-2.0.0`
Base: `9c94cea` (GFG Extreme 1.6.9)
Product version: 2.0.0 prerelease (alpha.1)

| Criterion | Result | How it was checked | Commit | If not passing |
| --- | --- | --- | --- | --- |
| Autopilot mode | PASS | Mode is in Governor. The selector offers Autopilot instead of Extreme. BudgetController still applies TDP. | this branch | |
| Planner | PASS | `tests/test_autopilot_v2.py` covers hold, CPU limit, unknown limit, heat, and a target that is not a measured FPS. | this branch | |
| Resource arbiter | PASS | A GPU-clock check freezes further TDP admission until accept or rollback. CPU power split is not stepped during that check. | this branch | |
| TDP | PASS | Autopilot does not write TDP itself. `autopilot` is a BudgetController mode. | this branch | |
| GPU clock | NOT_TESTED | Adapter uses the Steam Deck amdgpu files `power_dpm_force_performance_level` and `pp_od_clk_voltage`. Missing files return `GPU_CLOCK_UNAVAILABLE`. No physical Deck in this environment. | this branch | Needs a Deck where those files exist and a game is CPU-limited. |
| CPU power split | PASS | Split step is skipped while a GPU-clock check is open. | this branch | |
| FPS | PASS | Planner refuses to treat a 90 FPS target as measured Real FPS. Governor `TelemetryObserver` remains the only frame source. | this branch | The 1.7.1 field log had no renderer receipts at all. That still requires a game that is actually drawing frames. |
| Renderer ACK | PASS | Existing Governor confirmation path is unchanged. Autopilot does not invent an ACK. | this branch | |
| Rollback | PASS | Arbiter unit test rolls back a worse GPU-clock window and blocks an immediate retry. | this branch | Hardware restore of the previous GPU policy is NOT_TESTED. |
| HUD rings | PASS | Detailed preset adds GPU, CPU, TEMP, FRAME and does not add a second FPS or TDP ring. Green is not used when the frame sample is missing. | this branch | On-device placement at 1280x800 is NOT_TESTED. |
| Extreme removal | PASS | The mode control no longer offers Extreme. A saved `mode=extreme` becomes `autopilot` on load. Extreme code remains for the old tests. | this branch | |
| Profile migration | PASS | `MigrationTests` keeps `enabled` and rewrites only the mode. | this branch | |
| Diagnostics | PASS | Decisions go to the existing Governor JSONL via `_event`, and the 1 Hz timeline keeps the Autopilot fields. | this branch | |
| Regression | PASS | Local `unittest discover`: 1017 tests, 2 errors. Both are `os.chown` to uid 65534, which this sandbox rejects. They are not Autopilot failures. | this branch | Reconfirm on GitHub Actions. |
| Decky build | NOT_TESTED | Release workflow builds the zip. | this branch | |
| CI | NOT_TESTED | Recorded after the push. | this branch | |
| Steam Deck | NOT_TESTED | No device in this environment. | this branch | Run a game, confirm measured FPS, then Stop and confirm the previous TDP and GPU policy. |

Status: SOFTWARE READY / HARDWARE NOT VERIFIED
