# CPU/GPU Power Split: verified optimisation contract

Power Split restricts `scaling_max_freq` on **GFG-owned** CPU cpufreq policies, never the user's minimum or above their saved upper limit. It does *not* directly assign watts between CPU and GPU. It tests whether reducing peak CPU frequency can improve GPU headroom or reduce APU draw **at equivalent real-frame delivery**. CPU and GPU power are coupled through the Deck's APU and power cap, but freed CPU watts are not automatically consumed by the GPU.

## Phase 1: admissibility and clock ownership

Only a live, renderer-confirmed Governor point with settled power (not a TDP probe or a pending operating-point request), a GPU/power-limited scene, fresh Real FPS near the real-frame target and measured CPU headroom may start a CPU clock trial.

The CPU trial must yield to menu/loading, unknown critical CPU/real telemetry, GPU clock or VRS experiments, a new Governor point or TDP trial, manual external cpufreq changes and restore-pending state. Any such condition releases the CPU cap using the existing write-ahead journal, verified readback and external-ownership rules. An experiment is not proven by the successful sysfs write alone.

The CPU ladder is `100%, 85%, 70%, 60%, 50%`, never below the 1.6 GHz floor or the firmware minimum. Use one neighbouring level per validation cycle, even when the previous game session remembered a deeper cap. At every level, allow 3 seconds of settling and 10 seconds total of safe probing; a collapse to below 93% of the real target, a busiest core at 90% or a loss of telemetry removes or relaxes the cap. Cooling down prevents immediate retrials.

CPU ownership is claimed lazily when a nontrivial cap is actually requested. Pure observation does not claim and release sysfs each loop.

## Phase 2: isolated A/B/A

While the Governor remains steady and the current cap is held, compare capped → uncapped → capped at the same TDP, point and target. Each sampled phase covers at least 60% of an 8-second window and the switched phases wait 2 seconds for settling. Missing MHz, draw or Real FPS invalidate the comparison.

- Every phase must deliver at least 97% of the point's requested Real FPS.
- The capped mean must not lose more than 2% of the uncapped Real FPS (with a 0.5 FPS minimum tolerance).
- The two capped GPU-MHz-per-APU-Watt means must agree within 8%; greater drift suggests a different workload.
- `gain_pct` is **GPU clock per APU watt**, not a proven FPS or battery benefit. A nonnegative gain is not a licence to throttle the CPU permanently.

Four same-level matched pairs with 95% confidence upper bound below +1% stop the ineffective cap for a 10-minute per-level cooldown. The persistent game memory records a beneficial level **only** after three or more same-level comparable A/B measurements with a 95% lower bound above +1%, while the Real FPS protection was satisfied. Legacy memory from versions without the real-frame safety gate is invalidated rather than treated as evidence.

## Phase 3: hardware benefit and diagnostics

The native simulator and GitHub Actions verify state-machine safety, policy and CPU ownership, not whether a particular game saves APU watts on a physical Steam Deck. A fair device trial requires the same game/scene, target FPS, FG multiplier, screen refresh, temperature and TDP; alternate Power Split OFF/ON in matched, repeated windows, and compare:

1. Real FPS median and p95/p99 **real-frame** time, plus output delivery misses and visible quality. These are hard safety constraints.
2. Median APU draw and, for battery tests, discharge watts with charger state, fan and brightness controlled.
3. GPU clock and busy percentage, CPU top-core utilisation, applied policy caps and background workload.
4. Duration of actual held cap, successful A/B pairs per level, resets/rollbacks, ownership conflicts and any thermal regressions.

Conclude `measured battery gain` **only** from actual device power observations with equivalent real cadence; infer neither gain nor loss from GPU MHz/W, from an actuator request, or from synthetic input. The existing Frame OS Act, Governor and GSF are independent confounding controls and should not silently share a proof window.

## Known constraints

- cpufreq policies can map to several cores; limiting all of them can change thread scheduling or input latency. The busiest-core projection is a conservative heuristic, not a complete workload model.
- The Linux CPU frequency governor may run below the upper limit; a requested cap is not the observed CPU clock and need not save energy.
- A GPU MHz improvement without real-FPS improvement or lower verified power is GPU headroom only.
- The split is intentionally inactive during active Governor TDP exploration. Faster interleaving would require an explicit resource-arbiter lease that pauses the Governor's clock, watt and frame-quality probes together. Merely removing the stability check is not an acceptable shortcut.
- Power Split only writes CPU frequency limits. It does not change the user's GPU maximum clock or take ownership of Steam's TDP controls.
