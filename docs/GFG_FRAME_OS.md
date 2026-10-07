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
| **Control channel** | `/dev/shm/gfg-frame-os.<pid>` | 1–100 Hz | Fixed-layout struct: policy from the Governor in, telemetry out. Versioned, lock-free (seqlock). |
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

## 4. Phases and gates

| Phase | Deliverable | Gate before the next phase |
|---|---|---|
| 0 | This document; scheduler core with host tests; layer skeleton running through the Vulkan loader on a mock driver | Layer loads, intercepts, publishes telemetry in CI |
| 1 | Tick shaping + pacing in the layer; control channel; Governor reads telemetry | On a Deck: measured latency drop, no FPS loss, no stutter regression (needs a field log) |
| 2 | Adaptive real-frame injection + input sensor + energy broker driving Render v4 adaptive mode | On a Deck: fewer real frames in calm play at equal perceived smoothness, lower energy per minute |
| 3 | Tier 2 via OptiScaler for upscaler games | Separate design |

## 5. Safety rules (same as the Governor)

- Off by default; enabled per profile; the layer is a no-op unless the control channel says
  `enabled=1` with a matching version.
- Any internal error disables the layer's actions for the rest of the process (pass-through).
- Never blocks longer than one display refresh in a single wait; never changes game speed.
- Telemetry is local only.
