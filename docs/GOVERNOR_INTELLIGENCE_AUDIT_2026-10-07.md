# GFG Extreme — Governor Intelligence Audit
## 2026-10-07

Target reviewed: `main` @ `116cd6a036ac67919905476bc4c920d9fbb4a0a6` (Governor v0.0.8).

This audit supersedes the previous two audit documents.

## Product premise

GFG Extreme deliberately keeps **MAKO Render v4** as the execution engine.

The goal is not to replace Render v4. The goal is to build a Governor that behaves like a highly intelligent autonomous energy/performance orchestrator around it.

The optimization philosophy is:

> Minimize TDP while preserving a good gameplay experience. Use frame-generation multiplier, render scale and other runtime manipulations as compensation tools.

A high multiplier such as x3 is **not automatically a failure state**. If Render v4 produces a good experience at x3, Governor should be willing to prefer it when it materially reduces power.

The audit therefore asks:

1. Is Governor truly optimizing energy efficiency?
2. Is it modeling the game, or only walking a ladder?
3. Does it understand temporary spikes versus structural bottlenecks?
4. Can it compare multiplier / scale / TDP combinations intelligently?
5. Can it learn from previous sessions?
6. Can it explain why a decision is better?
7. Are monitoring, reliability and diagnostics strong enough for autonomous control?

---

# Executive conclusion

The current Governor is already significantly better than a simple toggle automation system.

It has:
- bounded trials;
- fresh-evidence windows;
- runtime overlays instead of destructive profile rewrites;
- power ownership;
- guard behavior;
- replay/unit coverage;
- live attach;
- deterministic reasoning.

However, it still behaves primarily as a **carefully engineered search controller**, not yet as a true adaptive game model.

The biggest opportunity is to move from:

`try point -> verify -> lower TDP -> guard`

to:

`observe -> classify -> predict -> choose -> verify -> remember`

The next major intelligence gain should come from **better observability, game modeling and utility-based decision making**, not from adding more toggles.

---

# 1. The objective function is still too narrow

Current behavior is heavily centered around:
- target output FPS;
- real/base cadence;
- pressure/misses;
- TDP floor search;
- quality-first candidate ordering.

That is reasonable, but it does not fully match the intended philosophy.

The real target should be:

> lowest sustainable power subject to a minimum experience-quality constraint.

This means x3 can be preferable to x2 if:
- output cadence is stable;
- real FPS is above the experience floor;
- frame pacing is acceptable;
- latency/artifact cost is acceptable;
- image quality is acceptable;
- power savings are meaningful.

## Recommendation

Introduce an explicit utility model:

```
utility =
    power_saving
  - real_fps_penalty
  - frametime_penalty
  - latency_penalty
  - generation_penalty
  - scaling_penalty
  - instability_penalty
  - thermal_penalty
  - transition_penalty
```

This does not require ML. The first implementation should stay deterministic and explainable.

---

# 2. Current ladder is still too “quality-first”

The current candidate ladder prefers lower multipliers first and only goes deeper when necessary.

That encodes the assumption:

> lower multiplier is always inherently better.

For GFG Extreme this is not necessarily true.

If x3 at 8 W feels good and x2 requires 13 W, the Governor should be allowed to select x3 deliberately.

## Recommendation

Replace pure ordering with candidate comparison.

Example:

| Point | Real | Output | Scale | TDP | Frametime | Stable | Utility |
|---|---:|---:|---:|---:|---:|---|---:|
| x2 | 45 | 90 | 100% | 14 W | 22.2 ms | yes | medium |
| x2.25 | 40 | 90 | 100% | 12 W | 25.0 ms | yes | high |
| x2.5 | 36 | 90 | 100% | 10 W | 27.8 ms | yes | very high |
| x3 | 30 | 90 | 100% | 8 W | 33.3 ms | yes | highest |
| x3 | 30 | 90 | 90% | 7 W | 33.3 ms | yes | mode-dependent |

The Governor should be able to conclude that x3 / 100% / 8 W is preferable when its experience floor remains satisfied.

---

# 3. Experience floors must be explicit

Output FPS is not enough.

The system needs explicit minimums for:
- real FPS;
- real frametime;
- frametime variance;
- output cadence stability;
- pressure/miss rates;
- maximum tolerated scaling;
- thermal margin.

## Suggested policy modes

### Quality
- strong preference for high real FPS;
- avoid deep generation unless needed;
- avoid scale reduction unless it buys a meaningful gain;
- tighter frametime/jitter limits.

### Balanced
- moderate real-FPS floor;
- allow x2.5/x3 when efficient;
- allow 90% scale when worthwhile;
- normal thermal/power bias.

### Battery
- lower real-FPS floor;
- aggressively use x3;
- allow stronger scale reduction;
- but never cross the experience floor just to save another watt.

Exact thresholds should be calibrated on Deck.

---

# 4. Monitoring is currently the biggest missing intelligence layer

A smart Governor cannot reason from FPS alone.

It needs a richer low-rate and high-rate observation surface.

## Required monitoring hooks

### A. Frame timing
Highest priority.

Collect:
- real/base frametime;
- output/present frametime;
- median;
- p95/p99;
- standard deviation or MAD;
- 1% low / 0.1% low equivalent;
- consecutive slow-frame count;
- stutter bursts;
- frame pacing regularity.

Why it matters:
Two states can both report “90 FPS” while one has clean pacing and the other is visibly awful.

Governor should distinguish:
- stable 33.3 ms real cadence feeding x3;
- 33 ms average with repeated 60–100 ms spikes.

### B. Temperature
Collect:
- APU temperature;
- GPU temperature if exposed separately;
- temperature trend, not only current value;
- thermal-throttling indicators.

Why:
A point can look healthy for 30 seconds and collapse after heat soak.

Governor should understand:
> performance is degrading because temperature is climbing, not because x3 is intrinsically bad.

### C. GPU load
Collect:
- GPU busy/utilization;
- GPU clock;
- GPU clock ceiling;
- residency/throttle signals if practical.

This is essential to determine whether render scale is likely to help.

### D. CPU load
Do not use a meaningless single “CPU %” number only.

Prefer:
- per-core utilization summary;
- highest-core utilization;
- effective CPU frequency;
- sustained CPU saturation;
- scheduler pressure/load average as supporting evidence.

A game may be CPU-bound with total CPU usage far below 100%.

### E. Actual power draw
Separate:
- configured TDP cap;
- measured APU/package power;
- battery discharge power.

A 10 W cap does not mean the game is consuming 10 W.

The Governor should learn both:
`allowed power` and `actually used power`.

### F. Battery telemetry
Collect when on battery:
- discharge watts;
- battery percentage;
- estimated remaining time;
- charge/discharge state.

Then the product can optimize for something users actually understand:
> this operating point gains 42 minutes for negligible experience loss.

### G. Thermal / electrical throttling
Collect indicators for:
- thermal throttle;
- power throttle;
- clock limiting;
- package limit pressure where available.

Do not treat throttled performance as a normal game-performance sample.

### H. Memory pressure
Lower priority, but useful:
- RAM usage;
- swap;
- memory pressure;
- VRAM/shared GPU-memory pressure if exposed.

This can explain stutters that multiplier/TDP manipulation cannot solve.

### I. Presentation/display state
Collect:
- active refresh rate;
- Gamescope mode;
- external display;
- VRR state/range if available;
- frame limiter state.

The target should derive from the actual presentation environment.

### J. Renderer health
Keep current Render v4 evidence:
- generated-delivery misses;
- bypass/recovery;
- pressure events;
- scheduler intervals;
- runtime-state-applied;
- fixed/adaptive plan;
- actual multiplier;
- actual scale.

These remain core signals.

---

# 5. Do not sample everything at the same frequency

A common failure mode would be to poll 20 sensors every frame and spend battery to save battery. A triumph of software engineering over purpose.

Use tiers.

## High frequency
Approx. 10–30 Hz where available:
- frame timing;
- renderer pressure/miss signals;
- output cadence.

## Medium frequency
Approx. 2–5 Hz:
- GPU load/clock;
- CPU load/frequency;
- power draw.

## Low frequency
Approx. 0.5–1 Hz:
- temperature;
- battery;
- memory;
- display state sanity checks.

Aggregate before feeding policy.

Governor should reason on windows, not raw noise.

---

# 6. Add a state estimator before the policy engine

Raw sensors should not directly drive actuator decisions.

Create an intermediate state:

```
SystemState:
  bottleneck
  thermal_state
  power_state
  pacing_state
  telemetry_confidence
  scene_stability
  headroom
```

Example classifications:

`GPU_BOUND | CPU_BOUND | POWER_BOUND | THERMAL | MIXED | UNKNOWN`

`PACING_CLEAN | PACING_UNSTABLE | STUTTER_BURST`

`THERMAL_COOL | WARM | HOT | THROTTLING`

This gives the policy engine something meaningful to reason about.

---

# 7. Governor needs a persistent game model

Suggested `GameModel`:

```
game_id
display_mode
renderer_version
config_fingerprint

native_capacity
likely_bottleneck
stable_points[]
failed_points[]
scale_effectiveness
tdp_curve
frametime_profile
thermal_profile
last_good_point
confidence
sample_count
last_updated
```

This turns each session into learning.

Next launch:
1. start near last-known-good;
2. verify;
3. adapt only if the environment changed.

No ML required.

---

# 8. Scale should be evaluated by observed benefit

Scale is not automatically bad.

It is useful when it creates enough GPU headroom to permit lower TDP or better cadence.

For each scale trial compare:

```
before:
real_fps
frametime_p95
gpu_busy
tdp
actual_power

after:
real_fps
frametime_p95
gpu_busy
tdp
actual_power
```

If 90% scale saves 2 W with tiny experience loss, excellent.

If 80% scale changes nothing in a CPU-bound game, mark it ineffective and stop trying it in future sessions.

---

# 9. Bottleneck classification should guide manipulation choice

Examples:

## GPU-bound
Prefer:
- scale reduction;
- possibly deeper FG;
- then TDP search.

## CPU-bound
Scale is unlikely to help.
Prefer:
- deeper FG if real-FPS floor allows;
- avoid unnecessary resolution loss.

## Power-bound
Be conservative with further TDP cuts.

## Thermal
Stabilize first.
Do not “learn” the hot throttled state as the game's normal capability.

## Mixed/unknown
Use conservative probing and lower confidence.

---

# 10. Target FPS should come from actual presentation state

Use:
- active refresh;
- external-display mode;
- VRR information if practical.

Fallback:
- OLED 90;
- LCD 60;
- external 60.

The fallback can stay simple, but it should no longer be the primary truth.

---

# 11. The cost model needs empirical calibration

Current weights are sensible placeholders, but they are opinions.

Calibrate them from real Deck sessions.

Particularly compare:
- x2 100% vs x2.5 100%;
- x2 90% vs x2.5 100%;
- x3 8 W vs x2 13 W;
- x3 100% vs x3 90%;
- stable average FPS vs cleaner frametime.

The key insight:
**frametime quality must have enough weight to defeat a superficially attractive low-TDP point.**

---

# 12. “Effort” should explain why the intervention is heavy

Keep Easy / Medium / Hard / Nightmare if desired, but attach reasons.

Examples:
- Hard — x3 required
- Hard — 80% scale required
- Hard — thermal margin low
- Hard — >15 W required
- Nightmare — target cannot be sustained
- Nightmare — real FPS below minimum floor
- Nightmare — frametime instability exceeds threshold

---

# 13. Real-session evidence must drive future tests

Replay/unit coverage is strong, but synthetic evidence can validate only the assumptions encoded by developers.

Create:
`tests/replay/real/`

Import minimized traces from actual Deck sessions:
- GPU-bound;
- CPU-bound;
- thermal soak;
- scene transition;
- shader compilation stutter;
- dock/external display;
- sleep/resume;
- QAM TDP conflict;
- PowerTools conflict;
- MangoHud coexistence;
- Flatpak;
- telemetry loss/recovery.

Rule:
**every real production bug becomes a replay fixture.**

---

# 14. Reliability findings from the first audit still remain valid

Even under the corrected product philosophy, several engineering issues should still be fixed.

## P1 — release workflow can skip validation after the tag exists
CI must run on every relevant PR/main commit regardless of release-tag state.

## P1 — release packaging does not rebuild/test frontend
Run frontend build and smoke test before packaging.

## P2 — privileged TDP helper can block indefinitely
Add bounded timeout/polling and bounded shutdown.

## P2 — frontend RPC failures can be silently swallowed
Expose failed actions and preserve clear UI state.

## P2 — stale runtime/documentation messages
Remove obsolete relaunch/old-version assumptions.

These are infrastructure issues, not philosophical disagreements.

---

# 15. governor_service.py is becoming too large

As intelligence grows, one giant orchestration service will become a liability.

Suggested boundaries:

### GovernorSupervisor
Lifecycle and RPC.

### TelemetryHub
Collects/normalizes renderer + hardware sensors.

### StateEstimator
Produces bottleneck/thermal/pacing/headroom classification.

### GameModelStore
Persistent learned behavior.

### GovernorPolicy
Ranks candidate operating points.

### RuntimeActuator
Multiplier/scale/runtime overlay.

### PowerController
TDP ownership/search.

### SessionEvaluator
Scores actual results and updates confidence.

This is the architecture that can support “super intelligence” without becoming spaghetti with a doctorate.

---

# 16. Recommended decision loop

The desired control loop should become:

```
OBSERVE
  ↓
ESTIMATE STATE
  ↓
LOAD GAME MEMORY
  ↓
GENERATE CANDIDATES
  ↓
PREDICT UTILITY
  ↓
CHOOSE BEST SAFE POINT
  ↓
APPLY
  ↓
VERIFY ON FRESH EVIDENCE
  ↓
UPDATE GAME MODEL
  ↓
LOCK / ADAPT
```

Not:

```
try x2
try x2.25
try x2.5
try x3
lower watts
```

The second can be correct.
The first is intelligent.

---

# 17. Suggested next implementation order

## Phase A — observability
1. Frametime windows and jitter/stutter metrics.
2. GPU utilization/clock.
3. CPU saturation/frequency.
4. Temperature and thermal state.
5. Actual APU/package draw.
6. Battery discharge power.
7. Active display refresh.
8. Telemetry confidence.

## Phase B — state estimation
1. GPU/CPU/power/thermal bottleneck classification.
2. pacing classification;
3. scene stability;
4. headroom estimate.

## Phase C — intelligence
1. explicit experience floors;
2. utility scorer;
3. candidate ranking rather than fixed ladder;
4. persistent GameModel;
5. learned scale effectiveness;
6. warm start from last-known-good.

## Phase D — validation
1. real Deck traces;
2. replay import;
3. calibrate thresholds/weights;
4. adversarial tests of x3 low-power modes.

---

# Final judgment

With the clarified product goal, keeping MAKO Render v4 is not an architectural weakness.

It is the foundation.

GFG Extreme's differentiation should be the intelligence around it.

The current Governor is already a strong deterministic controller, but to become the intended “super orchestrator” it needs to stop thinking mostly in terms of:

`multiplier + scale + TDP`

and start thinking in terms of:

`game state + bottleneck + frame pacing + thermal state + power efficiency + learned history + confidence`.

The most important next capability is therefore not another actuator.

It is **better observation**.

Once Governor can see frametime behavior, GPU/CPU bottlenecks, temperature, actual power draw and display state, the existing Render v4 actuator surface becomes dramatically more valuable.

That is the route from “automatic settings” to an actually intelligent runtime controller.
