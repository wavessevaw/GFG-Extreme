# Autopilot 2.0.0 acceptance

Branch: `feature/autopilot-2.0.0`
Base: `9c94cea` (GFG Extreme 1.6.9)
PR: #117

| Criterion | Result | Evidence | What is not claimed |
| --- | --- | --- | --- |
| Autopilot mode | PASS | Selector is Battery / Balanced / Quality / Autopilot. Saved `extreme` migrates to `autopilot`. BudgetController still owns TDP. | Not a Deck session. |
| Planner | PASS | `tests/test_autopilot_v2.py`: a target is not measured FPS; unknown limit holds; heat pauses; display goal changes only after three fresh misses. | Does not retune the screen refresh. |
| Resource arbiter | PASS | GPU-clock settle/verify blocks planned TDP admission, Flow and CPU split. A healthy HOLD does not start a new budget probe. Protective unhealthy budget path is unchanged. | Not a concurrent-thread stress test on device. |
| TDP | PASS | Autopilot does not write watts itself. | No measured watt change. |
| GPU clock writes | BLOCKED | `GpuClock.writes_enabled` is false in the service. `lower_ceiling` returns `writes-disabled` and does not touch sysfs. Mock backend covers partial write, failed restore, user override and receipt reload. | Real amdgpu writes stay off until a Deck proves restore. Reading the files is implemented. |
| GPU clock restore | PASS | Unit/integration: Stop, mode switch, game exit and a failed read-back keep or clear ownership as specified. Unconfirmed restore stays `RESTORE_PENDING` and blocks a new experiment. | Not verified against a live amdgpu node. |
| CPU power split | PASS | Planned split step is skipped while Autopilot blocks planned work. | Not a Deck CPU-cap trial. |
| FPS source | PASS | Planner uses Governor summary fields only. `instant` targets are not accepted as Real FPS. | The 1.7.x field log still had no renderer receipts. A game must actually draw frames. |
| Rollback | PASS | No measurable gain rolls back. Rollback does not clear the lock unless restore returns restored or yielded. | Hardware restore NOT_TESTED. |
| HUD | PASS | Detailed Autopilot rings: one FPS, one TDP, one BATTERY, plus GPU, CPU, TEMP, FRAME. All rings use green/yellow/red/grey. A bad frametime is not green. | 1280×800 placement NOT_TESTED. |
| Extreme removal | PASS | The mode control no longer offers Extreme. Extreme code remains for old tests. | |
| Profile migration | PASS | `MigrationTests`. | |
| Diagnostics | PASS | Decisions go through Governor `_event` JSONL and the timeline `autopilot` field. | |
| Regression | PASS | Local `unittest discover`: 1025 tests. Two `os.chown(65534)` errors are this sandbox rejecting that uid. They are not Autopilot failures. GitHub CI is the confirmation. One fingerprint test now changes multiplier to 4, because 3 was already the saved value and the file did not change. | |
| Decky build | NOT_TESTED | Release workflow on this commit. | |
| CI | NOT_TESTED | Previous runs 38058805574 and 38058808662 failed because the smoke needle was `AUTOPILOT` while the button text is `Autopilot`. | Re-run on the commit that contains this fix. |
| Steam Deck | NOT_TESTED | No device here. | Do not enable GPU clock writes for that run. |

Status: SOFTWARE READY / HARDWARE NOT VERIFIED, only after the GitHub checks on this commit are green. GPU clock actuation on hardware remains BLOCKED.
