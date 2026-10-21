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

## Smart power split (1.5)

CPU and GPU share one APU power limit, so the CPU's boost clock in a GPU-bound game costs the GPU
watts. `power_split.PowerSplit` (pure logic, injected clock) lowers the CPU's maximum clock through
a ladder (100 / 85 / 70 / 60 / 50 % of the maximum, floor 1.6 GHz, never above the user's own
limit). `cpu_freq.CpuFreqActuator` writes the ladder level to every cpufreq policy's
`scaling_max_freq`.

**When.** `GovernorService._sync_power_split` runs once per iteration. A step is possible only on a
live budget point at its watts (`_split_ready`, pinned to that point's key and real rate) with TDP
control, no Steam menu, no unfocused game and no Act injection. Anything else is *not eligible*:
the cap is lifted. A step down needs real frames ≥ 97 % of the point's real rate, a GPU-bound or
power-bound game, and the busiest core predicted ≤ 80 % at the lower clock
(`top × f_now / f_next`). Each step is a 10 s probe. Real frames under 93 % lift the cap at once
(after a 3 s settle) and start a 60 s cooldown. A busiest core ≥ 90 % steps back up one level, and
that level is blocked for 10 min when this happens during a probe or a dip.

**A/B.** While a level holds and the Governor is locked, every 60 s (240 s once 8 pairs exist) an
A-B-A runs: 8 s capped, 8 s (+2 s settle) at full clock, 8 s capped. A change of TDP or level
aborts it. The pair is the gain in GPU clock per watt (`mhz / draw`), plus the GPU clock and draw
deltas for the log.

**Memory.** `SplitMemory` is stored per game prefix in settings (`power_split_games`). It holds
the deepest held level (the next session's first stop), the last 40 pairs and the session counts.
At a session start, with at least 8 pairs from 2 or more sessions and a 99 % interval top under
1 %, the split is switched off for that game and re-checked after 8 sessions. *Reset what GFG
learned* clears it.

**Safety.** The actuator snapshots the policies at claim time and restores them on release,
`_restore_power`, game change and unload. A value changed by another tool pauses control without
restoring. Before every write a marker records the initial and written values, and the next start
restores any policy that still reads GFG's value. The root helper accepts only
`/sys/devices/system/cpu/cpufreq/policyN/scaling_max_freq` with 100 MHz–10 GHz values, and it puts
its last written values back when the plugin process goes away.

**Log.** The events `power-split` (step, reason, clocks, core and GPU load) and `power-split-ab`
(one pair). Timeline rows carry `power_split`, and `system.json` carries the cpufreq state. The
log summary reports the lowest clock, the capped share, why the cap came off, and the A/B result
with its interval.


## Extreme (1.6)

First stage (P0) of [EXTREME_FOUNDATION.md](EXTREME_FOUNDATION.md); contracts in
[EXTREME_CONTRACTS.md](EXTREME_CONTRACTS.md). Pure policy lives in `extreme.py`; the service owns the
lifecycle. Extreme is a fourth Governor mode run by `BudgetController(flavor="extreme")`.

**Power ceiling.** `extreme.power_ceiling` = min(15 W, the player's cap when GFG claimed the PPT
controls, the hardware maximum). `_budget_power` sets it as the actuator's ceiling override on every
step, so every write (`_apply_budget_tdp` with a Frame OS Act offset, recovery, the fast raise) is
clamped by `SteamDeckPowerActuator._set_tdp_w`. A cap changed outside GFG is an external change as
before; the re-claim snapshots the new value, which becomes the new ceiling
(`BudgetController.limit_power`). The controller starts at the ceiling and never searches lower
watts; spare headroom buys real frames (`reprobe-more-real-frames`). No x4 last resort, no watts
above the ceiling, real floor 30.

**Ladder.** `extreme_points`: every normal point (30 real .. native) at 80 %, 90 % and 100 % render
scale, sorted by (real cadence, scale). Upgrades buy real frames with resolution first and win the
resolution back on the next step; the guard gives up resolution before real frames. Scaled rungs
need the Scaling Engine provisioned at launch: Extreme makes every launch scale-ready
(`_scale_ready`), a game started before that gets `restart_required`. CPU-bound games, the
profile's own scaling, and Gamescope WSI compatibility keep full resolution.

**Scale + sharpening = one point.** `point_deltas(..., sharpness=)` writes `scaling_factor`,
`scaling_method` and `scaling_sharpness` (a live field since 1.6) into the overlay only. Sharpening
starts from `CAS_START` (90 % → 0.15, 80 % → 0.30) plus the player's correction
(`set_extreme_sharpness`, ±0.3, GFG settings, never Saved). It is 0 when vkBasalt CAS/DLS runs (no
double sharpening) and untouched when the profile scales on its own. A sharpening correction goes
live on the held point without a new trial.

**Acknowledgement (every budget mode since 1.6.1).** `TelemetryObserver` keeps bounded render-scale
evidence: the `swapchain-context-create` event (`application_width/height` against the presented
`width/height`), the scaler's `spatial scaling swapchain policy` line (`advertised_source`,
`actual_source`, `actual_presentation`, `inactive_reason`, `active`) and its `spatial scaling active`
line (with the applied sharpening). A third source is the renderer's runtime-state JSON next to its
config file (`<overlay dir>/runtime-state/*.json`, `spatial_scaling` block), filtered by the game's
PIDs (falling back to records written after the request when the game runs in another PID
namespace). A request whose render scale differs from the last acknowledged one is accepted only
when evidence newer than the overlay write shows the game rendering at the expected share of
native (the profile's own scaling included: `100 / scaling_factor`, ±3 points, uniform in both
axes). An inactive report rejects the point at once; no evidence within 20 s rejects it, and two
misses stop scaled trials for the session. A game whose swapchain ignores the advertised size
(`application-extent-override-no-source-presentation-split`, seen on a Deck) is remembered for
14 days in `scale_ignored_games`; *Reset what GFG learned* clears it. Sharpening counts as
confirmed only from the scaler's own report.

**Guard.** Since 1.6.1 a real stream clearly below the current cap goes straight to the highest
point whose cap the measured real frames reach (`_measured_deeper`), or the deepest usable one:
a field log showed three intermediate fractional points timing out in turn (75 s). Upgrades skip
render-scale rungs the launch cannot use (`_next_up`).

**Status.** `get_status().extreme` is a cached snapshot: state (OFF / DISCOVER / BASELINE / APPLY /
VERIFY / TUNE / ACTIVE / RESTART_REQUIRED / PAUSED), ceiling and its source, requested vs applied
point (render %, sharpening, source/output extent), the nine directions with state and reason
(`booster_states`), and `gain` with `kind: unavailable` until a same-scene A-B-A proof exists.
Battery/Balanced publish `extreme_offer` when the locked budget leaves ≥ 1.5 W of the ceiling
unused (no number promised). Frame OS Act follows Extreme only after the one-time consent
(`set_extreme_act_consent`), and leaving Extreme restores the previous Frame OS mode. The game
memory key carries the ceiling (`extreme-15w`), so a point learnt at 15 W is not reused at 12 W.
The session recorder and the log report carry state, ceiling, the highest cap read and the scales
the renderer confirmed.
