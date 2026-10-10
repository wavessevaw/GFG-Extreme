# Autopilot: first audit and diagnostic capture protocol

**Status:** Synthetic CI passed. The first physical Steam Deck **telemetry-only capture** was analyzed on 2026-10-10; no valid measured FPS was received and no Autopilot A/B/A actuator trial ran. Hardware PPT/Flow rollback is still NOT tested. See `docs/field-audit/20261010-first-deck/REPORT.md`.
**Target:** draft PR #115 over the consolidated Autopilot PR #114. Neither enables the development flags.

## Field log follow-up, 23:20 local time on 2026-10-10

A **second Steam Deck OLED capture on pre-alpha v1.7.1** has now confirmed that the renderer and the *legacy* Governor work: 74 fixed and 58 adaptive plan events, and legacy Governor power operations 20→12→13 W before restoration. **Autopilot itself is still blocked**: 439 independent observation ticks, zero verified real-FPS evidence, zero A/B/A trials or Autopilot actuator writes. The producer emits `base_fps`, which the strict C1 reader intentionally does not treat as verified `current_base_fps`. Do not synthesize evidence from planner FPS. Full privacy-sanitized numerical report: `docs/field-audit/20261010-second-deck/REPORT.md`. The original full ZIP remains private.

The earlier first physical log (v1.7.0) failed even to produce a renderer FPS stream. **Neither physical run verifies Autopilot actuator restoration.**

## Evidence chain

One recording must preserve cause and effect rather than only a displayed FPS number:

| Evidence | Source / file | What must be visible |
|---|---|---|
| Render receipts | `diagnostics-*.log` | raw fixed/adaptive-plan, measured real/output FPS, frame generation pressure, context, stage |
| Autopilot observations | `autopilot-trace.jsonl` | monotonic receipt timestamp, original event sequence, blocked reason, plan/action/strategy, flags |
| Decision and scheduler | `autopilot-trace.jsonl` | slot owner, phase A1 / APPLY / SETTLE / B / RESTORE / A2 / VERDICT, ACK expectation, samples, stale/drop |
| Actuators and safety | `autopilot-trace.jsonl`, `activity.jsonl`, `governor-events.jsonl` | requested/observed slow+fast PPT, pre-trial baseline, ceiling, ownership, restore results, Flow Saved request and ACK seq |
| Timeline | `timeline.jsonl` | 1 Hz Governor + Autopilot state, current profile, point, decisions, blocked reasons, sensors and power |
| Environment | `self_test.json`, `system.json`, `game-processes.json` | SteamOS/kernel, Gamescope, device, active Vulkan layers, launch wrapper, preconditions |
| Source and changes | `launch-wrapper.sh`, `profile.json`, `overlay/*`, `activity.jsonl` | profile values, runtime overlay, user actions, launch mode, relevant settings |
| Power and thermals | `power-sensors.json`, `timeline.jsonl` | slow/fast cap and APU draw, temperature, GPU load, CPU constraints, before/after snapshots |
| Plugin faults | `plugin.log`, `summary.txt` | Python errors, failed restores, missing telemetry, suggested diagnostics |

An **unavailable** sensor or unmeasured latency must stay unavailable. Output FPS must not be inferred from the target or multiplied base FPS. Only fresh renderer receipts count as independent evidence.

The trace is JSONL and bounded to 8 MiB, with the last 2 MiB retained upon rotation. Its source write errors never block the Governor and are counted in `autopilot_debug.trace_failures`. The diagnostic ZIP exports at most 8 MiB of trace from the recording offset and includes `autopilot-trace-meta.json`; a long recording or source rotation may truncate the earliest events. Start the recording **before** the suspected incident.

## First safe device capture

1. Use the ordinary GFG Extreme build with **both Autopilot development flags disabled**. Confirm the Steam Deck has battery/thermal headroom and can run the chosen game normally.
2. Open the existing **Diagnostics / Log recording** controls. Run the setup check. Press **Start** *before* launching the game.
3. Launch a game through the GFG launch wrapper and play for at least two representative scenes, including a menu/focus transition. Keep the recording running during a profile change or a return to Steam if those are the behaviors under investigation.
4. Press **Stop**. The recorder writes `~/Desktop/GFG-Extreme-log-YYYYMMDD-HHMMSS.zip`. Ensure the ZIP has all evidence listed above and `autopilot-trace-meta.json`. Record the exact Git commit/build, SteamOS version, model, game and timestamp separately.
5. If `autopilot-trace.jsonl` is empty, report that explicitly. It means no observation ticks were captured, not that all checks passed. Check `self_test.json`, `plugin.log`, the trace metadata and the renderer log.

**Do not enable the development power/flow flags for this first capture.** They still lack a safe cold-start bootstrap and have not been verified on physical Deck hardware. No physical TDP or renderer-scale experiment is authorized by this CI workflow.

## Mandatory safety matrix before enabling Autopilot

- A/B/A: real unique receipt sequences, A1, +1 W, verified slow+fast PPT ACK, settle B, restore, ACK, settle A2, verdict.
- Power ownership: initial user PPT, current pre-trial PPT, hard ceiling, external controller, rounded or partial write, rollback retry and correct lease release.
- Flow: Saved scale, requested and actual resources, correct context and `ack_seq > mark`, stale ACK, timeout, rollback and lost renderer.
- Context changes: menu focus, disabled/reenabled flag, both flags enabled, direct flow-to-power and power-to-flow, profile switched, new game / renderer generation / launch-key change.
- Telemetry: stale sample, same receipt counted once, missing FPS or sensor, zero output, backlogged/rotated log, false output/real gain.
- Safety: every early return/exception must leave no unverified temporary cap, flow scale or CPU limit. A failed restore must visibly block the next writer.
- Fault injection: write denied, readback mismatch, missing Saved profile, corrupted memory data, no ACK, log full or unwritable, plugin restart/unload.
- Restore baseline and session markers must not be overwritten merely by observing the new session.
- Any real acceptance must use device logs; mock CI alone cannot certify rendering, latency, power or perceptual visual quality.

## CI first run, with evidence even if tests fail

```sh
python3 scripts/autopilot_audit_run.py --outdir artifacts/autopilot-first-run
```

The dedicated GitHub Actions job runs the Autopilot, Governor Flow, restore barrier, runtime and SessionRecorder test suites. It always uploads `summary.json`, `test-run.log`, `test-events.jsonl`, `README.txt` (even on test failure). `summary.json` includes the SHA, duration, environment, test count and explicit `hardware_verified=false`.

A **successful CI run** means only that the synthetic regression tests passed. The first physical field log proves the instrumentation emitted 490 JSONL records over ~166 seconds, but still had zero game FPS samples, zero A/B/A trials and zero Autopilot actuator writes. It is not evidence that a physical Steam Deck performed a treatment and restore.

## Privacy and evidence integrity

The standard bundle contains system paths, a game/process inventory, launcher and profile data. Review it before sharing publicly; never upload credentials or account secrets. Preserve the raw ZIP and original timestamps, attach a SHA256 checksum when moving it, and analyze copies rather than editing the source log.

## Audit conclusion / release gate

The implementation is an **instrumented scaffold**, not a working production Autopilot. The uploaded physical 1.7.0 build had power flag ON and Flow flag OFF, but Governor was DISABLED throughout; do not conflate this with the default flags of PR #115 source, which remain OFF. Identify the exact deployed build/commit before investigating source parity. Do not merge as a 2.0.0 release or expose a UI switch on the basis of synthetic CI. Require a documented on-device rollback/ACK matrix, the real ZIP, and no unresolved P0 safety findings.
