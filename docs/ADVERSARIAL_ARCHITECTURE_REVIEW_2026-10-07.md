# GFG Extreme — adversarial architecture & product review
## Super-critical pass — 2026-10-07

Target reviewed: `main` @ `116cd6a036ac67919905476bc4c920d9fbb4a0a6` (Governor v0.0.8).

This document intentionally takes the opposite posture from a normal code review. It asks:
- Is the product solving the right problem?
- Is the architecture becoming harder than the value it creates?
- Are we proving real performance or only proving our own model?
- Are we building GFG Extreme, or an increasingly elaborate controller around MAKO?
- What should be deleted, simplified, or redesigned before v0.0.10?

No production code is changed here.

---

# 1. The central criticism: GFG Extreme is currently an orchestrator, not an independent frame-generation technology

The repository presents a distinct GFG product and calls the renderer path “GFG Engine”, but the shipping renderer payload is still:

`MAKO-Renderer-v4.0.0-linux.tar.xz`

from upstream:
`eugeniosegala/MAKO`

The package metadata explicitly downloads and bundles that renderer release.

That means the most differentiated code in this repository is currently:
- runtime orchestration;
- automatic multiplier/scale selection;
- telemetry interpretation;
- TDP optimization;
- wrapper/layer composition;
- UX.

Those are useful, but they are not a new frame-generation algorithm or renderer.

## Why this matters

If the strategic goal is “make MAKO dramatically easier and smarter”, the architecture is heading in a valid direction.

If the strategic goal is “GFG Extreme should become a genuinely new technology with better efficiency than MAKO/LSFG”, the project is currently spending most engineering effort above the layer where the actual competitive breakthrough must occur.

## Recommendation

Make the product decision explicit.

### Path A — GFG Extreme = best autonomous MAKO/LSFG runtime
Own it. Stop implying renderer independence. Focus on:
- one-button operation;
- automatic quality/latency/power tuning;
- compatibility;
- diagnostics;
- per-game learned profiles.

This can become an excellent product much sooner.

### Path B — GFG Extreme = new frame-generation runtime
Then Governor work should temporarily stop expanding.

Create a real renderer/runtime workstream with:
- owned Vulkan layer/runtime;
- explicit telemetry ABI;
- explicit live-control ABI;
- measured interpolation cost;
- generated-frame quality metrics where feasible;
- reproducible benchmark harness;
- side-by-side MAKO / LSFG-VK / GFG measurements.

My recommendation: treat A as the near-term product and B as a separate research track. Do not pretend they are already the same project.

---

# 2. The Governor optimizes a proxy, not the player's experience

Today the core question is effectively:

> Can this operating point hold target output FPS with acceptable renderer pressure at the lowest TDP?

That is neat, deterministic and testable.

It is also incomplete.

90 generated FPS from 30 real FPS is not equivalent to 90 native FPS.
60 generated FPS from 20 real FPS can look smooth while control response feels awful.
A point with lower render scale may hit the target while image quality becomes visibly worse.

The Governor currently has stronger mathematical confidence about “output FPS target reached” than about:
- input latency;
- real-frame latency;
- interpolation artifacts;
- frame pacing visible at presentation;
- motion quality;
- image quality after scaling;
- whether a game genre can tolerate the selected real FPS.

## Recommendation: optimize a utility function, not output FPS alone

The decision model should eventually consider:

`utility = smoothness - latency_cost - FG_cost - scaling_cost - instability_cost - power_cost`

Not necessarily machine learning. A transparent deterministic policy is fine.

But it needs first-class constraints such as:
- minimum real FPS;
- maximum multiplier;
- maximum scaling loss;
- user priority: Quality / Balanced / Battery;
- genre or per-game latency sensitivity.

For example:

### Quality
- minimum real FPS: 40–45
- prefer native / <= x2
- scaling only when necessary
- never degraded 20x3

### Balanced
- minimum real FPS: 30
- up to x3
- scale 90% before deep FG
- normal power optimization

### Battery
- minimum real FPS: 24
- deeper FG allowed
- scale 80% allowed
- aggressively search TDP

This is much more honest than one universal ladder.

---

# 3. Hard-coded 90/60 targets are product-friendly but technically too simplistic

The public model is:

- OLED = 90 FPS
- LCD = 60 FPS
- Dock/external = 60 FPS

That makes the UI simple.

But an external display is not inherently 60 Hz.
An OLED Deck can be operating at a different refresh.
VRR changes what “target” even means.
A user may deliberately select 45 Hz, 72 Hz, 80 Hz, etc.

A Governor that claims to “know your screen” should derive its target from the **actual active presentation mode**, not from the product name.

## Recommendation

Make target selection:

1. Read actual Gamescope active refresh.
2. Detect VRR and usable refresh range.
3. Pick target from presentation state.
4. Only use 90/60 as safe defaults when display information is unavailable.

Then UI can still say:
> Target: 90 FPS

but it is a measurement, not a hard-coded identity.

---

# 4. The fractional multiplier ladder may be more clever than useful

The automatic grid currently includes:

`1.0, 1.25, 1.5, 1.75, 2.0, 2.25, 2.5, 2.75, 3.0`

Conceptually this gives fine control.

Operationally it creates many trial states, more transitions, more evidence windows, more code paths, and more assumptions about renderer behavior.

Before hardware validation, this may be premature optimization.

## Criticism

The project has designed a sophisticated search space before proving that every fractional mode:
- behaves correctly on real hardware;
- has predictable latency;
- produces worthwhile visual quality;
- has reliable telemetry;
- is materially better than a much smaller ladder.

## Recommendation

For v0.0.10 hardware validation, drastically reduce the automatic ladder:

OLED:
- native 90
- 45x2
- 36x2.5 or 30x3
- optionally 45x2 at 90% scale
- degraded fallback only if explicitly enabled

60 Hz:
- native 60
- 40x1.5
- 30x2
- 24x2.5
- 20x3 only in Battery mode

Then gather real data.

Only add fractional points that show a real Pareto improvement in:
- power;
- latency;
- visual quality;
- stability.

Otherwise the extra states are architecture tax.

---

# 5. The project is overfitting to synthetic/replay evidence

The test suite is a real strength.

But there is a dangerous psychological trap here: a deterministic controller plus a deterministic replay suite can become extremely good at passing scenarios invented from the controller's own assumptions.

The documentation admits that hardware validation is still pending and that replay lines are modeled on renderer format strings rather than captured Deck sessions.

That means many tests currently prove:

> the code behaves consistently under our model

not:

> the model describes reality.

## Recommendation

From this point onward, test coverage should grow primarily from **real captured failures**.

Create:
`tests/replay/real/`

Every hardware session should produce anonymized/minimized traces such as:
- OLED stable;
- OLED CPU-bound;
- OLED GPU-bound;
- shader-heavy;
- bad frame pacing;
- Dock 60;
- external 120 Hz;
- game launch/exit race;
- sleep/resume;
- Steam QAM TDP interaction;
- PowerTools conflict;
- MangoHud enabled independently;
- Flatpak game;
- telemetry rotation;
- renderer crash.

Rule:
**a production bug is not fixed until its captured trace becomes a replay regression.**

That will turn the replay framework into a real asset instead of an elaborate simulation.

---

# 6. Diagnostics-log parsing is the wrong long-term telemetry transport

Current telemetry relies on tailing renderer diagnostic logs because no explicit shared-memory ABI was confirmed.

This is acceptable for a prototype.

It is not an ideal control-plane interface.

Logs are designed for humans/debugging, not deterministic low-latency feedback loops.

Problems:
- format can change;
- buffering can change;
- disk/log I/O exists in the hot path;
- rotation/truncation becomes application logic;
- telemetry freshness depends on logging cadence;
- parsing text consumes CPU for data the renderer already has structurally;
- native/x1 may provide insufficient periodic evidence.

The amount of code needed to make the log tailer trustworthy is itself evidence that the transport is wrong.

## Recommendation

If GFG controls the renderer in the future, create a tiny versioned telemetry ABI.

Preferred options:
1. shared-memory ring buffer;
2. Unix domain socket;
3. memfd/shared mmap;
4. compact local datagram stream.

Example record:
```
version
sequence
monotonic_ns
base_fps
output_fps
multiplier
present_interval
generated_misses
pressure_flags
active_scale
runtime_generation
```

The Governor should consume structured samples directly.

Keep diagnostics logs for humans.

---

# 7. Control plane and data plane are too entangled inside GovernorService

`governor_service.py` has become very large and owns too many responsibilities:
- lifecycle;
- settings;
- device/display detection;
- telemetry orchestration;
- overlay ownership;
- HUD synchronization;
- operating-point trials;
- TDP search;
- power ownership;
- journaling;
- event logging;
- live attach;
- restore semantics;
- status shaping;
- session behavior.

This is moving toward a “god service”.

Large orchestration files feel efficient during rapid development because everything is in one place. Later they become the place where every fix breaks three unrelated things. Humanity has performed this experiment before.

## Recommendation

Before adding more features, split it around stable boundaries:

### GovernorSession
One game/profile session state machine.

### GovernorPolicy
Pure decision logic:
- target;
- candidate ranking;
- guard decisions.

### RuntimeActuator
Applies/reverts:
- multiplier;
- base cap;
- scale;
- runtime config.

### PowerController
Owns TDP only.

### TelemetrySource
Versioned input interface.

### DisplayTarget
Refresh / dock / VRR decisions.

### GovernorSupervisor
Lifecycle and Decky RPC facade only.

The service should become orchestration glue, not the entire product.

---

# 8. “Saved / Effective / Actual / Governor runtime” is correct but cognitively expensive

Architecturally, keeping Saved configuration separate from runtime state is excellent.

Product-wise, four different configuration realities are difficult for users and agents.

If the system frequently needs an Inspector to explain which reality is real, the model may be too exposed.

## Recommendation

Internally keep all four.

Externally simplify to:

- **Your settings**
- **GFG live adjustment**
- **What the game is actually using**

Three layers are understandable.

The deeper Saved/Effective distinction can live in Doctor/Developer diagnostics.

---

# 9. The UI promises more certainty than the backend possesses

Examples of product language:
- “Knows your screen”
- “real data”
- “stops once target is held”
- “Saves battery”
- “always restores”
- “one Run button”

As product copy this is attractive.

As engineering truth in a pre-hardware-validation beta, some claims are too absolute.

The backend itself knows about:
- missing telemetry;
- unverified native points;
- process-static toggles;
- overlay limitations;
- external ownership;
- Flatpak complexity;
- TDP access failure.

## Recommendation

Keep the simple UI, but make confidence a first-class state.

Examples:
- Ready
- Measuring
- Verified
- Limited telemetry
- External controller detected
- Could not verify
- Needs restart

Internally attach:
`confidence = verified | inferred | unknown`

Do not present inferred behavior as measured behavior.

---

# 10. The Governor should learn per game instead of rediscovering everything every session

Today the architecture intentionally uses bounded exploration.

That is safe.

But repeatedly testing the same known-bad operating points every launch wastes time, power and user patience.

The project already has journaling/session infrastructure. It is close to having persistent learned profiles.

## Recommendation

Persist a lightweight **Game Capability Cache** keyed by:
- Steam app ID / executable;
- display target;
- renderer version;
- major config fingerprint.

Store:
- last stable point;
- last stable TDP;
- rejected points;
- observed native capacity;
- confidence/sample count.

Next launch:
1. start near last-known-good;
2. verify;
3. only re-explore if conditions differ.

This gives the system the behavior users expect from something called “smart”.

No ML required.

---

# 11. TDP optimization is missing CPU/GPU bottleneck awareness

The Governor primarily sees renderer cadence and power caps.

But reducing TDP in a CPU-bound title and reducing TDP in a GPU-bound title are different problems.

The telemetry document explicitly says GPU/CPU clocks/utilization and temperature/package telemetry are not integrated.

Without bottleneck classification the system can observe “FPS got worse” but cannot understand why.

## Recommendation

Add low-rate host telemetry:
- GPU busy;
- CPU utilization/frequency summary;
- GPU frequency;
- APU power;
- temperature;
- throttling state.

Do not use it to build a giant PID controller.

Use it to classify:
- GPU-bound
- CPU-bound
- power-bound
- mixed
- unknown

Then adjust candidate preference.

Example:
- GPU-bound: render scale may help more than deeper FG.
- CPU-bound: render scale may do almost nothing.
- power-bound: TDP reduction should stop early.
- thermal throttling: avoid interpreting degradation as a bad FG point.

---

# 12. Render scale should not be treated as a generic performance lever

Current logic tries 90% and 80% scaling to free GPU time.

That can be correct for GPU-bound games.

For CPU-bound games it can simply reduce image quality without improving real FPS.

Until bottleneck telemetry exists, scaled trials are partially blind.

## Recommendation

At minimum, require evidence that scale helped:
- compare real FPS before/after;
- reject scale if performance improvement is below a threshold;
- remember this per game.

Better:
only prioritize scale when GPU-bound evidence exists.

---

# 13. The current quality model is hand-authored opinion presented as policy

`CostModel` assigns penalties such as:
- multiplier penalty;
- scale penalty;
- degraded penalty;
- transition penalty.

This is transparent, which is much better than opaque ML.

But the values are still arbitrary until calibrated.

For example, is 80% scale really “6 units” worse than 100%?
Is x3 “4 units” worse than x2?
Is a point transition worth 5?

Those numbers can silently encode product behavior.

## Recommendation

Rename them mentally from “cost model” to “policy weights”.

Then calibrate them from hardware/user experiments.

Create benchmark fixtures where humans choose A vs B:
- x2 @ 90% scale vs x2.5 @ 100%;
- x3 @ 10 W vs x2 @ 14 W;
- 30x3 vs 45x2 under unstable scenes.

The weights should reflect actual preference.

---

# 14. The “Effort” rating is attractive UX but currently scientifically weak

Easy / Medium / Hard / Nightmare is a nice user concept.

But current classification combines power, multiplier and scale using fixed thresholds.

This risks becoming decorative certainty.

“Nightmare” at one configuration may simply mean:
- telemetry issue;
- CPU bottleneck;
- wrong target refresh;
- poor renderer support;
- game menu/scene transition.

## Recommendation

Keep the feature, but redefine it as:
**GFG intervention level**, not game difficulty/performance truth.

Example:
- Light
- Moderate
- Heavy
- Limit

Or preserve the existing labels but expose what caused them:
> Hard: ×3 generation required
> Hard: 80% render scale required
> Hard: >15 W required

That makes the label explainable.

---

# 15. The product has too many historical layers in the repository root

The root contains many:
- old release notes;
- old test reports;
- Beta notes;
- GFG2/GFG3/GFG31/GFG4 notes;
- hardening notes;
- multiple product-generation documents.

This is useful archaeology and terrible current-state documentation.

Agents can easily read the wrong “authoritative” file.

## Recommendation

Restructure:

`docs/current/`
- ARCHITECTURE.md
- TELEMETRY.md
- LIMITATIONS.md
- RELEASE_PROCESS.md
- HARDWARE_VALIDATION.md

`docs/history/`
- old notes/reports/releases

`docs/audits/`
- audit documents

Root should contain only:
- README
- license/notices
- package/plugin metadata
- current release description if required by automation.

Make it impossible for an agent to accidentally implement v0.0.1 assumptions into v0.0.9.

---

# 16. Release-number-driven development is becoming artificial

The repository has issues mapped mechanically to v0.0.2, .3, .4 ... .10 with alternating “feature / audit” structure.

That discipline helped prevent uncontrolled changes.

But software does not naturally divide itself into decimal rituals.

A release should represent a coherent user-visible capability or validation milestone, not merely the next turn of an agent crank.

## Recommendation

Keep feature/audit pairing internally, but move to milestones:

- **M1 Control-plane reliability**
- **M2 Real hardware telemetry**
- **M3 Stable auto-quality**
- **M4 Stable battery optimization**
- **M5 Production UX**

Version only when something shippable changes.

---

# 17. v0.0.10 should not be “first real hardware test”

This is the biggest process criticism.

Hardware is not an integration checkbox to perform after nine software versions.

The Governor controls:
- frame pacing;
- Vulkan runtime behavior;
- display behavior;
- TDP;
- renderer configuration.

These are hardware/runtime-dependent by definition.

Continuing significant architecture changes until v0.0.10 without iterative Deck validation risks validating the wrong architecture very thoroughly.

## Recommendation

Change the plan immediately.

Before adding another major Governor feature:
1. install current v0.0.8 on a real Deck;
2. capture several real sessions;
3. compare UI status to actual behavior;
4. import traces into replay tests;
5. fix discrepancies;
6. only then design v0.0.9.

The next milestone should be **evidence**, not more code.

---

# 18. What I would simplify immediately

Freeze new features and make a “v0.0.9 Reality Check” release.

It should do only this:

1. Dedicated CI on every PR.
2. Hardware trace capture improvements.
3. Actual refresh-derived target.
4. Clear confidence/telemetry state.
5. Root-helper timeout.
6. RPC error visibility.
7. Real-session replay import format.
8. Remove stale docs.
9. Benchmark only 4–5 operating points.
10. No new fancy Governor features.

Then test it on Deck.

---

# 19. What I would build after real validation

If real traces validate the architecture:

## Phase 1 — Reliable autonomous controller
- per-game capability cache;
- actual refresh target;
- quality/balanced/battery policy;
- minimum real-FPS constraint;
- bottleneck classification;
- stable session history.

## Phase 2 — Better runtime interface
- replace diagnostics-log telemetry with structured IPC;
- explicit renderer live-control ABI;
- explicit capability/version negotiation.

## Phase 3 — GFG-owned renderer research
Only if independent GFG technology is still the goal:
- benchmark harness;
- owned Vulkan runtime;
- interpolation experiments;
- latency and quality measurement;
- compare against MAKO/LSFG-VK.

---

# 20. Final judgment

## What is good

The project has evolved from a pile of toggles into a coherent control-system concept.

Strong ideas:
- Saved state is protected from runtime experimentation.
- runtime changes are reversible;
- TDP ownership tries not to fight external controllers;
- search is bounded instead of endlessly oscillating;
- decisions are explainable;
- tests/replay exist;
- UI is aiming at a single-action product rather than exposing every knob.

That is real progress.

## What worries me

The project is accumulating controller sophistication faster than it is accumulating real-world evidence.

The biggest current risks are not syntax bugs.

They are:
1. optimizing the wrong objective;
2. validating against synthetic assumptions;
3. relying on a debug log as telemetry infrastructure;
4. hard-coding product targets that should come from live display state;
5. expanding a god-service;
6. spending large effort on Governor intelligence while the actual frame-generation engine is still upstream MAKO.

## My recommendation

Do **not** make v0.0.9 another feature release.

Make it the release where GFG Extreme stops reasoning about an imaginary Steam Deck and starts reasoning from a real one.

If v0.0.8 behaves correctly on hardware, the current architecture deserves investment.

If it does not, now is the cheap moment to simplify it.

After hardware validation, decide explicitly whether GFG Extreme is:

**the smartest autonomous controller for MAKO/LSFG**

or

**a new frame-generation technology with its own renderer**.

Both are valid products.

Trying to be both without separating the roadmaps will create a huge codebase whose most sophisticated component is deciding how to operate someone else's renderer.
