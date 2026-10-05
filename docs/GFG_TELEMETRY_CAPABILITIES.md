# GFG Telemetry Capabilities — Governor v0.0.1 Beta

Status: initial capability spike against the bundled GFG Extreme v4.0.0-gfg.4 / MAKO Renderer v4 binary.

## Baseline

- Host platform: GFG Extreme v4.0.0-gfg.4.
- Renderer payload: bundled MAKO Renderer v4.
- Governor must treat GFG 2.x only as historical experience.
- No planner behavior is implemented from assumptions. Only observed runtime evidence is eligible.

## Confirmed renderer diagnostics

The current renderer binary exposes structured present-diagnostics events including:

- `adaptive-plan`
- `fixed-plan`
- `runtime-state-applied`
- `runtime-transition-pending/prepared/applied/failed`
- `generated-delivery-miss`
- `generated-admission-pressure`
- `generated-admission-recovered`
- `pipeline-busy-bypass`
- `pipeline-busy-recovered`
- `render-fence-budget-missed`
- `ordered-acquire-budget-exhausted`
- `gamescope-refresh-rate-applied`
- `gamescope-presentation-feedback`
- `present-breakdown`

The binary also contains diagnostic fields that can support Governor capacity/stability models:

- `base_fps`
- `target_fps`
- `rearm_baseline_base_fps`
- `previous_base_fps`
- `current_base_fps`
- `previous_output_fps`
- `current_output_fps`
- `baseline_base_fps`
- `instantaneous_base_fps`
- `threshold_fps`
- `projected_output_fps`
- `measured_base_fps`
- `observed_output_fps`
- `configured_adaptive_target_fps`
- bypass / miss counters.

## Existing diagnostics transport

GFG Extreme gfg.4 already enables the renderer diagnostics through:

- `MAKO_PRESENT_DIAGNOSTICS`
- `MAKO_PRESENT_DIAGNOSTICS_LOG`

and ships `gfg-diagnostics`, which reads the retained present diagnostics log and already knows the relevant operation names.

At this stage no explicit `/dev/shm`, `shm_open`, memfd, JSONL telemetry channel, or shared-memory telemetry contract was found in the current renderer binary strings.

### Beta decision

The first Governor Observer should therefore use an **incremental diagnostics-log reader**:

1. keep file identity + offset;
2. read only newly appended bytes;
3. never rescan the complete diagnostics file on every sample;
4. attach a monotonically increasing Observer sequence to parsed fresh evidence;
5. survive log rotation/session replacement;
6. expose one normalized cached snapshot to Planner, Guard, UI and tests.

Do not create multiple independent telemetry readers.

## Capability matrix

| Metric / evidence | Current evidence | Planned reliability |
| --- | --- | --- |
| Real/base FPS | Confirmed diagnostic fields (`base_fps`, `measured_base_fps`, `instantaneous_base_fps`) | High for GFG backend after parser validation |
| Output FPS | Confirmed diagnostic fields (`observed_output_fps`, `current_output_fps`) | High for GFG backend after parser validation |
| Generated FPS | Not yet confirmed as a direct numeric field | Derive only if renderer emits sufficient fresh plan/present evidence; otherwise leave unavailable |
| Effective multiplier | Plan/runtime-state evidence exists; exact field format still needs sample validation | Medium until live/replay sample confirmed |
| Misses | Confirmed event: `generated-delivery-miss` | High |
| Bypasses | Confirmed bypass/recovery events and counters | High |
| Admission pressure | Confirmed pressure/recovery events | High |
| Fence pressure | Confirmed `render-fence-budget-missed` | High |
| Refresh | Confirmed Gamescope refresh events | High |
| Renderer application state | Confirmed runtime transition/state-applied events | High |
| GPU/CPU usage/clocks/power/temp | Not supplied by renderer diagnostics | Must come from SteamOS/sysfs or another existing host source; capability spike still required |
| Frametime variance | No direct normalized field confirmed yet | Compute only from a validated timing source; do not invent |
| OptiScaler real/generated FPS | Not confirmed | Observer-only where evidence exists; never infer internal FG activity from config alone |
| Game-native FG counters | Not confirmed | Unavailable unless an external source proves them |

## Evidence rules

- Re-reading a cached line/sample is not fresh evidence.
- Requested config is not proof of applied renderer state.
- Stale `runtime-state-applied` evidence must not validate a newer transition.
- Telemetry loss pauses optimization; Governor must not continue changing TDP/multiplier/scale blind.

## Next implementation step

Implement the Observer and replay parser before Planner logic.

Required first replay fixtures:

- stable_native_90
- stable_45x2
- stable_30x3
- stable_dock_60
- temporary_spike
- sustained_pressure
- telemetry_loss
- stale_samples

Only after the parser and Fresh Evidence semantics are deterministic should the Capacity/Stability models and Operating Point planner be added.
