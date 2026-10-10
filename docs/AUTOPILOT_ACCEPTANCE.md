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
| Decky build | PASS | Release run on code commit `0e770b85496f9a6d75ce828eb32765a0bed83310`: https://github.com/wavessevaw/GFG-Extreme/actions/runs/38059744675. Asset `GFG-Extreme-v2_0_0.zip`, sha256 `f6279cbff229f0336215f35800c5c720b5680ad368a8f38724b58878b7957e47`. Prerelease, not latest. | This docs commit does not change the package. |
| CI | PASS | Push https://github.com/wavessevaw/GFG-Extreme/actions/runs/38059745004 and PR https://github.com/wavessevaw/GFG-Extreme/actions/runs/38059748801 on `0e770b8`. The earlier failure was the smoke needle `AUTOPILOT`; the selector text is `Autopilot`. | Reconfirm this docs commit on its own CI run. |
| Steam Deck | NOT_TESTED | No device here. | Do not enable GPU clock writes for that run. |

Status: SOFTWARE READY / HARDWARE NOT VERIFIED on code `0e770b8`. GPU clock actuation on hardware remains BLOCKED.
