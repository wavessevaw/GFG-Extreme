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

## Playtime target (1.4)

`playtime.PlaytimePlanner` turns "the battery must last N hours" into an APU ceiling every Governor
step: `energy_Wh x 0.95 / hours_left - others_W`, where `others_W` (screen, memory, fan) is the
smoothed battery discharge minus the APU's measured draw (4.5 W until measured). The ceiling moves
in 0.5 W steps with 0.6 W hysteresis. `BudgetController.set_playtime_cap` lowers the normal,
ideal and emergency ceilings to it (never below the Deck's minimum) and pulls the current TDP down;
every TDP write passes through `_sync_playtime_cap`, so nothing bypasses it. Inside the ceiling the
guard keeps the output by moving to deeper generated-frame ratios, as at the normal ceiling.
States: `holding`, `on-track` (no limit needed), `tight` (cannot be met; `reachable_min`),
`charging`, `reached`. The target and its wall-clock deadline persist in the settings.

**Playable first (1.4.2).** Field report: a long target put a heavy game at 6 W, 10 real frames
shown as 30. `_playable_guard` watches the real frames while the playtime ceiling is binding; below
92 % of the mode's real floor (24 Battery / 30 Balanced) for 6 s it raises the ceiling by 1 W and
stores the level per game (`playable_w`, settings). The planner never sets a ceiling below it; a
target that would need less is `limited`, with the realistic `reachable_min`. A new session starts
0.5 W lower to re-check. `PlaytimePlanner.options` offers targets from this game and this charge:
1.15x / 1.3x / 1.5x the current pace and *Max* (the longest playable time), in 10-minute steps.

**Proven before lowered (1.4.3).** 1.4.2 learned `playable_w` only after the ceiling had already
starved the game once. Now the floor is also `BudgetController.proven_w`: the lowest TDP at which
the game held its point (a healthy window, a binding held level, or the warm-start level from an
earlier session), else the start level (10 W Battery, the Balanced start in Balanced). The planner
uses `max(playable_w, proven_w)`, so the ceiling only follows the Governor's own search down to
levels that kept the point; a target that would need less is `limited` until they are proven.
