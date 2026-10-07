# GFG Frame OS — architecture (working draft)

Status: in development on a branch, not shipped. Nothing here is enabled in a release.

## 1. The shift

Today GFG is a Decky plugin that *configures* a frame-generation engine (Render v4, a Vulkan
layer whose frame generation is Lossless Scaling's LSFG) and moves TDP. Every decision is
coarse (seconds) and indirect (a config overlay the engine re-reads).

Frame OS moves the decision point **into the frame pipeline**. A GFG-owned runtime sits
between the game and the presentation path and decides, frame by frame, *when* the game may
start work, *which* frames are real, *how* they are presented, and *how much energy* each
part of the pipeline gets. Render v4 becomes one executor among several.

```
 game (simulation + render)
   │  vkQueueSubmit / vkAcquireNextImageKHR / vkQueuePresentKHR
   ▼
 ┌──────────────────────── gfg-pacer (GFG Vulkan layer) ────────────────────────┐
 │  sensors:  CPU frame time · GPU frame time (timestamps) · present feedback      │
 │            input intensity (evdev, via control channel) · power                │
 │  core:     Presentation Scheduler  (frame timeline, deadlines, decisions)      │
 │  actions:  gate frame start (tick shaping) · pace present · real-frame plan    │
 └──────────────────────────────────┬──────────────────────────────────────────────┘
                                    ▼
 Render v4 executor (FG ratio / adaptive target, scaling)  →  driver  →  Gamescope
                                    ▲
 Governor (Decky, slow loop, seconds): policy, power, memory, UI ── control channel (shm)
```

## 2. Components

| Component | Where | Rate | Role |
|---|---|---|---|
| **Presentation Scheduler** | `engine/gfg-pacer/src/scheduler.c` | every frame | Owns the frame timeline. Predicts the next present, decides when the game may start its next frame, and whether the next frame must be real. Pure C, no Vulkan types: unit-tested on the host. |
| **Layer glue** | `engine/gfg-pacer/src/layer.c` | every frame | Implicit Vulkan layer. Hooks acquire/present, measures, sleeps where the scheduler says, publishes telemetry. |
| **Control channel** | `/dev/shm/gfg-frame-os-<pid>` | 1–100 Hz | Fixed-layout struct: policy from the Governor in, telemetry out. Versioned, lock-free (seqlock). |
| **Policy (Frame OS policy)** | `py_modules/gfg_plugin/frame_os/` | 10–20 Hz | Input intensity, scene-change detection, real-frame injection plan, energy budget broker. Writes targets into the control channel. |
| **Governor** | existing | 1 Hz | Mode, TDP ceiling, game memory, UI. Becomes the outer loop of the broker. |
| **Executors** | Render v4, Scaling Engine, PPT caps | — | Do what the scheduler/policy decide. |

## 3. The ideas, by what they need

The constraint that decides everything: GFG has **no source of the game** and, today, **no
source of Render v4** (binary `libmako-render.so`; FG is closed LSFG). What a layer can see
without game cooperation is: when the game submits and presents, how long the GPU took, the
final colour image, and the player's input.

### Tier 1 — game-agnostic, needs only our layer (building now)

1. **Game-agnostic Dynamic Tick Shaping** — the core of Phase 1. The scheduler delays the
   moment the game *starts* its next frame so that it finishes just before its present slot
   (just-in-time). The game's simulation speed is unchanged; the queue of finished-but-waiting
   frames disappears, so input→photon latency drops by up to a whole real-frame interval.
   Same principle as NVIDIA Reflex / AMD Anti-Lag, done in a layer for any Vulkan game.
2. **Presentation scheduling / pacing** — present real frames on a deadline grid with
   measured jitter compensation instead of "as soon as ready".
3. **Adaptive Real-Frame Injection** — the real cadence stops being a fixed `output /
   multiplier`. The scheduler raises the real rate (and the executor lowers the ratio) when a
   real frame matters: input spike, fast camera motion (from input), scene cut (detected from
   GPU-time/brightness discontinuity), UI interaction; and lowers it in calm stretches. The
   executor for a variable ratio already exists: Render v4's *adaptive* mode holds an output
   target with a variable real cadence. "Multiplier" becomes an outcome, not a setting.
4. **Render Budget Broker** — instead of "TDP 10 W", an energy budget per window ("2.1 J for
   the next 200 ms") split between real frames, scaling and FG, with the PPT cap as the hard
   ceiling. Calm windows bank energy, action windows spend it.
5. **Predictive Presentation (timing)** — predict the next present time 1–2 frames ahead from
   the frame timeline and input trajectory, so pacing and tick shaping act before a hitch, not
   after.

### Tier 2 — needs depth and motion vectors (only games with an upscaler, via OptiScaler)

Games that ship FSR/DLSS/XeSS hand depth, motion vectors and jitter to the upscaler; OptiScaler
already intercepts that call. Through it, and only for those games:

6. **Frame Cache / Temporal Reuse** — keep depth/motion/stable-region history; skip or cheapen
   regions provably unchanged.
7. **Object-/layer-aware generation** — HUD from the UI pass separately from the 3D image.
8. **Multi-resolution temporal rendering** — importance from depth + motion + screen centre.
9. **Image extrapolation** (predict the next frame instead of interpolating between two) —
   removes FG's built-in one-frame delay.

These need our own FG executor (FSR3-FG-class, MV based) beside LSFG.

### Tier 3 — needs the game's own engine (not game-agnostic)

10. **Decoupled simulation/presentation** beyond what FG already does: the simulation rate is
    owned by the game loop; a layer can only throttle it (tick shaping), not re-time it.
11. **Speculative rendering** of several camera states: requires re-rendering the scene with
    different cameras — only the engine can do that.

Kept on the map; no work until there is an engine integration path (e.g. a plugin SDK for
specific engines).

## 3a. What the field logs say (evidence, 2026-10-07)

`tools/frame_os_breakdown.py` over three recorded Deck sessions (~31 000 real frames, 30 real x3
at 90 Hz, Render v4 interpolation):

| per real frame | p50 | p90 |
|---|---|---|
| present call holds the game thread (`total_ms`) | 20.5–21.1 ms | 21.7–21.9 ms |
| of which: waiting to show the generated frames (`acquire_ms`) | 19.7–20.3 ms | 20.7–21.0 ms |
| of which: waiting for the game's GPU work (`render_fence_ms`) | 0.02 ms | 0.04–6.5 ms |

Consequences:

* With interpolating FG the game has **no queue** for tick shaping to remove: it is already held
  inside present while the executor shows the frames generated *before* the new real one. The
  latency is the FG hold itself, ≈ (multiplier − 1) × output slot: x3 ≈ 22 ms, x2 ≈ 11 ms.
* So the strongest latency lever is the **real cadence**: Adaptive Real-Frame Injection (x3 → x2 in
  motion) removes ~11 ms exactly where the player feels it. Priority over tick shaping.
* Tick shaping stays useful where a queue exists: native (x1) points, games with deeper
  swapchains, FG executors that do not hold present.
* The next large step is in the executor: **show the real frame first** (extrapolate the generated
  frames *after* it instead of interpolating before it). That needs executor work (Tier 2 or a
  Render v4 change) and is where Predictive Presentation leads.

## 3b. Executor contract for real-frame injection (Phase 2 design)

Rewriting the renderer config per stick flick is not an option (config rewrites take seconds to
confirm, and a burst of live config changes has crashed a game before). Instead:

* The Governor applies, once per point, Render v4 **adaptive mode** with the output target (90)
  and a real-frame cap at the **boost** level (45): the renderer may receive up to 45 real frames
  and fills the rest to the target.
* gfg-pacer, sitting **above** Render v4 in the layer chain, gates the game's real frames on its
  slot grid: 30 Hz in calm play, 45 Hz while the policy boosts. The renderer sees a variable
  real cadence and adapts its generated-frame count; no config write per decision.
* Layer order: implicit layers load in directory-listing order, which differs per filesystem.
  The launcher names both layers in `VK_INSTANCE_LAYERS` (pacer first) and clears both implicit
  enable variables; that is the only setup that held with both listing orders on loaders
  1.3.275, 1.4.321 and 1.4.365 (`make -C engine/gfg-pacer ordering`, stand-in 2x frame
  generator: the pacer sees N presents, not 2N). The layer is 64-bit only (`library_arch`), and
  Flatpak sandboxes need it staged plus a shared `/dev/shm` before it can run there.

Deck experiment that gates Phase 2: adaptive mode at target 90 / cap 45, layer pacing switching
30 <-> 45 every few seconds; measure output stability, generated-frame misses and transition
artefacts from the renderer's own diagnostics.

## 4. Phases and gates

| Phase | Deliverable | Gate before the next phase |
|---|---|---|
| 0 ✅ | This document; scheduler core with host tests; layer through the real Vulkan loader on the mock driver (headless swapchain); control channel v2; Governor wiring behind a per-profile switch | Done: `make -C engine/gfg-pacer test layer integration` |
| 1 | **Observe, then shadow on a Deck**: the layer in the real chain above Render v4, telemetry (freshness, present intervals) in recorded logs | 30+ min clean sessions: no picture change, no pacing/latency effect, game exit, swapchain recreation, suspend/resume |
| 2 | **Adaptive real-frame injection** (input sensor + energy broker, adaptive-mode executor contract above) | On a Deck: lower freshness in motion, equal smoothness, energy within the premium |
| 3 | Tick shaping for native points / deeper queues; executor work on showing the real frame first | Separate design |
| 4 | Tier 2 via OptiScaler for upscaler games | Separate design |

## 5. Safety rules (same as the Governor)

- Off by default; enabled per profile; the layer is a no-op unless the control channel says
  `enabled=1` with a matching version.
- Any internal error disables the layer's actions for the rest of the process (pass-through).
- A frame-start wait never exceeds `max_wait_ms` (the Governor sets 80 % of one real-frame slot, e.g.
  26 ms at 30 real); a present hold never exceeds one real-frame period. Never changes game speed.
- Rollout modes: `observe` (measure only), `shadow` (scheduler runs, never sleeps: would-be
  decisions), `act`. A profile moves to the next mode only after the previous one ran clean on a Deck.
- Telemetry is local only.
