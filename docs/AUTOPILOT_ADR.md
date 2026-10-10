# ADR: Autopilot C0/C1 observation boundary

Date: 2026-10-10. Status: accepted for the observation development slice only.
Specification: owner's GFG Autopilot engineering assignment, revision 2026-10-10.
This is not a completed Autopilot implementation or a release candidate.

## Baseline and coexistence

Refs were read from GitHub before changes: main
`90f3f3aa2056342a31f705194600f003de4497f8` (1.6.7), tree
`c001d1aa55961086a72ab29706bff341d9de3be8`.
Open PR #97 head `5c3d7c0acf5a01fc4e6de9b4450ac8f3705f0053`,
`release/stable-1.6.8-efficiency`, contains overlapping telemetry, flow,
service and diagnostics corrections. Do not overwrite or merge that branch.
Reconcile its final accepted changes before C2. PR #92 is data-only DO NOT MERGE;
#78 is historical design, not authority for universal 15 W caps; #58 is an older HUD proposal.

Work branch: `autopilot/c1-observation-20261010`, based on freshly read main.
No version bump, mode-selector migration, actuator change, release trigger,
main merge, tag or publication is part of C1.

## Decision

Use separate immutable contracts, deterministic perception, a bounded raw-event
tap, and a cache-only adapter. GovernorService remains the lifecycle owner.
C1 observes the existing active Governor session and exposes
`get_governor_status().autopilot_observation` in Details. It is a diagnostic
development slice, **not a selectable or independently runnable Autopilot mode**.
Existing Battery/Balanced/Quality/legacy Extreme decisions remain authoritative.
C1 owns no actuator and does not create/configure a Frame OS runner.

Do not consume legacy diagnosis or summary FPS as independent measured evidence.
On main, explicit measured output zero can fall back to a planned value in the
legacy parser; PR #97 fixes that path. C1 taps raw fields before that conversion
and preserves zero without altering legacy parser behavior. Fixed-plan real FPS
derived from output divided by a configured ratio is not an independent real
measurement. C1 reports it unavailable. Scheduler requested intervals are not
physical presentation intervals. `base_fps` alone has insufficient provenance.

The tap accepts bounded-context generation events, explicitly rejects spatial
roles, retains at most 64 samples and 64 pressure events, and resets on observer
session changes. No second log tailer is added. HostSensors includes the time
and sequence of actual acquisition, unchanged on cached returns. Errors cannot
make old samples fresh.

The adapter invalidates on profile/backend/launch identity (including PID start
identity), renderer generation/context, target changes, menu/focus uncertainty,
clock gaps and pending restoration. It conservatively requires a recent launch
probe and focus evidence. After invalidation, old samples cannot form a new
baseline. Coalesced log reads count once per receipt timestamp, not once per line.
Pure perception requires increasing sequences/times, a minimum duration and
sample count, current renderer and host data, and corroborating evidence.
Thresholds live in immutable Config and are not device-validated tuning.

CPU/GPU/FG results are moderate-confidence correlated hypotheses, not proof of
the causal bottleneck. STABLE means the reported delivery target held in this
window, not verified smoothness, visual quality or latency.
No presentation-limited verdict is synthesized from requested interval p95.
Thermal/power hypotheses require explicit verified limits/draw in the contract;
the C1 runtime adapter cannot supply that provenance and leaves them unavailable.

## Known evidence limits

* Renderer diagnostic time is log receipt time, not producer capture time.
  Initial backlog is skipped by the existing observer; multiple lines received
  together cannot establish a sustained window. Delayed writer buffering still
  cannot prove current producer age. Therefore **C1 evidence cannot authorize control**.
* Existing focus reports may be sparse; UNKNOWN is expected once confidence in
  current focus expires. Do not weaken freshness merely to make the card look active.
* A context-bearing event is required. Older diagnostics with no renderer context,
  or only reconstructed real cadence, yield unavailable/UNKNOWN.
* No reliable scene/cutscene/loading detector exists. Changing scenes can produce
  ambiguous hypotheses; no learning/trial outcome is written from them.
* APU draw and cap values in existing status lack sufficient acquisition/context
  metadata for this adapter. Battery discharge is not substituted for APU draw.
* C1 is passive only with respect to Autopilot: existing enabled Governor modes
  still control their actuators. The diagnostic card states this explicitly.
* UI integration shares existing status polling, not a second poller.
* Observation has no disk persistence, unbounded log or learned model. It cannot
  erase/convert Extreme or Frame OS memory.
* Hardware tests, physical input-to-photon, subjective image quality, and control
  loop overhead on Deck remain NOT_TESTED.

## Capability and ownership matrix

| Existing subsystem | Source | C1 | Required before control |
|---|---|---|---|
| Renderer telemetry | governor_telemetry.py | raw reported FPS, context, receipt time | producer freshness, request revision and fresh ACK chain |
| Host sensors | host_sensors.py | acquisition time/sequence, optional loads/temp | device identification and verified safety limits |
| TDP | governor_power.py, privileged_power.py, steamos_tdp.py | no calls/writes | hardware/user/thermal min; lease; readback; explicit restore outcome |
| CPU cap | cpu_freq.py, power_split.py | no calls/writes | shared reservation, A/B/A invalidation, marker recovery |
| Renderer/scale | governor_overlay.py, governor_confirmation.py, extreme.py | no request/benefit claims | provisioning, source/output/sharpening ACK separately |
| Flow | governor_flow.py, service _sync_flow | no tuner | wrap existing A/B/A in shared reservation |
| Frame OS | frame_os/runner.py, proof.py, engine/gfg-pacer | no runner/config/control changes | existing explicit Act consent; scheduler handoff and return |
| Game memory | game_model.py, frame_os/memory.py | untouched | separate bounded versioned fingerprints; accepted outcomes only |
| Display | existing display probe | target participates in context | no Hz writes in P0-P2 |
| OptiScaler/Game Native | configuration fg_backend | UNKNOWN/observe-only; cached GFG data invalidated | no current actuator contract |
| Saved profiles | configuration service | read-only existing status integration | Effective only; ownership-safe undo |

## Blocking C2 findings

1. Existing _restore_power does not propagate every failed power restore into
   _restore_pending; legacy _release can announce DISABLED after incomplete
   power restoration. Autopilot must aggregate actuator restore results before
   implementing Stop/mode transition.
2. Legacy _scale_gate accepts same/native scale without a new source ACK.
   That cannot satisfy the Autopilot restore confirmation contract.
3. Flow, Power Split and Frame OS exclusion gates are local rather than a unified
   reservation protocol. No second controller may start before this is resolved.
4. Source-time provenance and contextual measured draw are incomplete.
5. Reconcile PR #97's measured-zero/role/ACK changes without duplicating or
   reverting them.

## Migration and following scoped PRs

C1 does not change the schema or selector. Next: C2 pure constrained policy and
optimizer plus a single-flight A/B/A engine, followed by explicit ownership-safe
restore aggregation and two verified actuator adapters. Revalidate ACK on every
request and rollback before moving to the next trial. Never route autopilot
through FLAVORS/BudgetController extreme.

C3 reserves all incompatible existing tuners and consented Frame OS actions.
C4 adds separate versioned fingerprint storage and opt-in constraints, default
minimum render 90%, explicit 80% consent, then a one-time selector-only migration
after full readiness. Preserve power/scale/filter/HUD/Frame OS/per-profile choices.
No Extreme model becomes confirmed Autopilot evidence. Mode change blocks until
restoration is confirmed. Legacy code remains for rollback.

C5 runs complete CI and native checks, packages with the repository release
builder, verifies CRC/checksums/native assets, and records a Deck field matrix.
No release/merge without owner authorization. No candidate is offered to the
owner before internal checks pass.

## Test plan and honest labels

New tests: tests/test_autopilot_perception.py (pure inference),
tests/test_autopilot_runtime.py (real telemetry parser/tailer, host caching,
adapter, and Governor status integration), tests/fixtures/autopilot_observation.json,
and existing frontend smoke extended for zero/missing/reported output.

Cases: stable 90/HOLD-equivalent observation; high GPU alone; CPU/GPU corroboration;
zero/absent/NaN; plan-only/derived real; stale/future time; repeated/coalesced sample;
pressure freshness and uniqueness; unknown thermal/power; spatial isolation;
session/PID start/Hz/profile/generation/backend change; focus/menu; suspend gap;
restore-pending; corrupted/missing evidence; bounded queues; no Saved/settings writes.

Run unchanged .github/workflows/ci.yml: generated config, all Python tests,
native pacer/HUD mock Vulkan ABI/integration/ordering, archived timing/HUD
benchmarks, npm build with committed dist equality, Chromium frontend smoke.
These are SIMULATED checks, never DEVICE-VERIFIED.

Deck matrix remains blocking NOT_TESTED: LCD/OLED, 60/90 Hz, CPU/GPU-heavy games,
battery/charger, user TDP change, hot scene, QAM, external backend, restart/exit,
ACK disappearance/return, suspend/dock. No performance benefit is claimed.

Development environment has GitHub API access but no shell/Python/Node executor.
Validation must be evidenced by GitHub Actions results on the exact commit;
writing tests alone does not count as running them.
