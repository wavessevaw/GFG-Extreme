# GFG Governor v0.0.1 Beta Architecture

GFG Governor is a runtime orchestration layer inside GFG Extreme v4.0.0-gfg.4. It does not replace ConfigurationService, backend ownership, Pipeline Inspector, Config Journal, Automatic Dock, or the existing renderer contract.

## Policy

The control loop is intentionally quiet:

`Observe -> Prove -> Choose -> Optimize Power -> Lock -> Intervene only when necessary`

Handheld target is 90 output FPS. External display/Dock target is 60 output FPS. Automatic candidate points are bounded to Native, x2 and x3. x4/x5 are never Governor choices.

## Beta components

- `governor_telemetry.py`: one incremental MAKO diagnostics reader. It skips old backlog when attaching, survives rotation/truncation, publishes monotonic sample/event revisions, and computes P1/P5/median/MAD.
- `governor_core.py`: pure deterministic Operating Point policy, transparent cost model, and non-oscillating coarse-to-fine TDP search.
- `governor_power.py`: ownership-aware Steam Deck fastPPT/slowPPT actuator. It snapshots the existing user cap as the ceiling, never raises above it, and stops controlling power if another component changes PPT.
- `governor_service.py`: Decky runtime orchestration and RPC surface.
- `tools/gfg_governor_replay.py`: offline deterministic replay of renderer evidence.

## First-Beta actuation boundary

v0.0.1 Beta does **not** automatically persist or rewrite profile multiplier, base cap, or render scale. The Planner can recommend a different point, but power optimization starts only when live telemetry proves that the running game already matches the proven point. This preserves the gfg.4 Saved / Effective / Actual boundary and avoids turning a runtime controller into a profile mutation loop.

When the point matches, Governor may claim PPT control and find minimum stable TDP. If the point cannot be confirmed, the state remains `PLAN`. If PPT controls are unavailable, it remains `OBSERVE_ONLY`.

## TDP ownership

At claim time Governor snapshots fastPPT and slowPPT. Those values are the session ceiling. Each subsequent write is allowed only while sysfs still equals Governor's last expected values. If Steam QAM, PowerTools, another plugin, or the user changes PPT, ownership is released and Governor pauses rather than fighting the external controller.

On clean disable/unload Governor restores the original caps only when it still owns them.

## Runtime states

- `DISABLED`: per-profile Governor is off.
- `PROBE`: gathering enough fresh evidence.
- `PLAN`: a recommendation exists or target viability is being evaluated, but the runtime point is not yet confirmed.
- `OPTIMIZE_POWER`: testing lower PPT levels with fresh evidence windows.
- `LOCKED`: minimum stable power found; no further optimization occurs.
- `GUARD`: current point was unhealthy at the available/user ceiling.
- `OBSERVE_ONLY`: external FG backend or unavailable TDP actuator.
- `PAUSED`: stale telemetry, external TDP change, or a runtime error.

## Non-goals for Beta 1

No ML/bandit/RL, no x4/x5 automation, no game-settings editing, no automatic OptiScaler configuration, no GPU clock control, no overclock/undervolt, and no hardware limit unlocking.
