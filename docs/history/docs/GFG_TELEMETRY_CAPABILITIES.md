# GFG Telemetry Capabilities — Governor v0.0.1 Beta

Initial capability spike against the bundled GFG Extreme v4.0.0-gfg.4 Renderer v4.

## Confirmed renderer evidence

Structured diagnostics include `adaptive-plan`, `fixed-plan`, `runtime-state-applied`, runtime transition events, `generated-delivery-miss`, admission pressure/recovery, pipeline bypass/recovery, fence budget misses, ordered acquire budget exhaustion, Gamescope refresh/presentation feedback, and present breakdowns.

Confirmed numeric field names in the current renderer include `base_fps`, `target_fps`, `measured_base_fps`, `instantaneous_base_fps`, `current_base_fps`, `observed_output_fps`, and `current_output_fps` plus scheduler interval statistics.

## Transport decision

The existing gfg.4 wrapper already enables `MAKO_PRESENT_DIAGNOSTICS` and `MAKO_PRESENT_DIAGNOSTICS_LOG`. No explicit stable `/dev/shm`/memfd telemetry ABI was confirmed in the current Renderer v4 binary. Beta therefore uses an incremental diagnostics-log tailer. It reads only appended bytes, skips historical backlog at initial attach, detects rotation/truncation, and keeps bounded sample/event caches.

A legacy `/dev/shm/gfg-present-diagnostics.log` is accepted only if it actually exists and is newer; it is not assumed.

## Fresh evidence

Re-reading cached state is never fresh evidence. Samples and events receive monotonically increasing revisions. Each new TDP candidate is evaluated only against samples/events emitted after that candidate was applied, so pressure from the previous power level cannot poison the new test window.

## Current metric availability

| Metric | Beta source | Status |
| --- | --- | --- |
| Real/base FPS | renderer base/interval fields | available |
| Output FPS | measured output, scheduler interval fallback | available |
| Effective multiplier | output/base or coherent scheduler intervals | available |
| Generated FPS | output minus base | derived |
| Misses/bypasses/pressure | structured renderer operations | available |
| Renderer application evidence | plan/runtime transition events | available |
| GPU/CPU clocks/utilization | host telemetry | not integrated yet |
| temperature/package power | host telemetry | not integrated yet |
| internal Game Native FG | game-specific | unverified |
