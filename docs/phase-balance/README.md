# Balanced phases before an early real frame

GFG Extreme 3.6.1-phase.1 bundles Kedavra 1.8.1-phase.1. The candidate starts from contour.1. In fixed 60 Hz ×2 and fixed 90 Hz ×3 with a 30 FPS cap, Silk can already present a ready real endpoint early. When an input interval stretches by one refresh, the last generated sample can sit too close to the preceding frame. This build shifts the sample towards the middle of the remaining movement. The readiness check requires the next source pair to be known. The maximum shift is three eighths of a refresh. At 90 Hz the longer interval must recur. An exact midpoint keeps its existing low-cost warp path.

The source queue, flip decisions, GPU passes, shaders and number of generated frames are the same as contour.1. No input lookahead or blur was added. The exported phase numerator and denominator report the actual sampled fraction. The trace position tracks the scheduler playhead.

## Scheduler replay

Each run covers 180 simulated seconds, discarding the first four. The fixtures feed the actual scheduler identical source latches and analysis completions. Error is the deviation from one display period of movement per refresh for a constant-velocity object. A lower RMS means more even motion. It does not measure FPS. The regression checks the source IDs and output kind at every refresh, monotonic movement and exact preservation of previously scheduled midpoints.

| Display and game | RMS step error, contour.1 → phase.1 | P95 step error |
|---|---:|---:|
| 60 Hz, 24 FPS | 0.3381 → 0.2219 | 0.667 → 0.354 |
| 60 Hz, 27 FPS | 0.2174 → 0.1759 | 0.332 → 0.306 |
| 60 Hz, 28 FPS | 0.1596 → 0.1456 | 0.330 → 0.330 |
| 90 Hz, 28 FPS | 0.1979 → 0.1886 | 0.406 → 0.330 |
| 90 Hz, 29 FPS | 0.1301 → 0.1201 | 0.353 → 0.353 |
| 90 Hz, smoothly varying 28–32 FPS | 0.1725 → 0.1703 | 0.356 → 0.344 |

Both 30 FPS lock tests produced identical decisions and sample phases. At 90 Hz with 24 or 27 FPS and in the 90 Hz hitch scenario the candidate made no difference. All twenty configurations, including stalls and late motion analysis, passed the invariants. The production scheduler still owns the latency and ×2/×3 policies. The historical OLED flip traces in the engine repository predate the candidate.

## Rendered courtyard reversal

The first changed pair in the 28 FPS replay supplied these display patterns. For ×2 the intermediate moved from 5/12 to 1/2. For ×3 the phases moved from 1/4 and 9/16 to 1/4 and 5/8. The offline stress test repeats **this affected pattern** over all seven pairs of the ray-rendered courtyard at 1280×800, keeping the real frames and the reference time of each display slot identical. Real usage includes many unaffected pairs. The ground truth includes acceleration and reversal. The tracker measures lateral movement of visible foreground bars through the real endpoints and intermediate phases on matched observations.

| Comparison | ×2 | ×3 |
|---|---:|---:|
| RMS bar step error, pixels | 5.92 → 3.44 | 5.59 → 4.30 |
| Matched steps | 104 | 156 |
| Missing intermediate bar observations | 1 → 1 of 56 | 4 → 3 of 112 |
| Mean temporal image error | 16.15 → 11.89 | 20.31 → 17.20 |
| Severe 4×4 blocks vs reference | 7.05% → 3.74% | 7.88% → 5.86% |
| Interior block outliers on the separate bad-block metric | 10.48% → 13.32% | 9.81% → 11.22% |

A separate 480×300 replay exposed a false scene cut on the sixth irregular interval: both intermediates repeated the older frame. Changing the phase cannot correct a held picture. Three shader alternatives (changing the endpoint bias, weighting neighbouring block confidence and changing motion-field reprojection) did not address this hold. The release candidate preserves the contour.1 shaders.

[Slow-motion comparison with the rendered reference](reversal.mp4) · [Same-slot crop](reversal.png)

## Execution cost and device check

The host ran llvmpipe with four workers. The timing replay alternated both phases on the same pair, four repeats per build per slot, reversing the initial order between pairs. The measured warp times in milliseconds are software Vulkan timestamps.

| Mode | Samples per build | Median | P95 | P99 |
|---|---:|---:|---:|---:|
| ×2 | 28 | 60.28 → 57.91 | 85.12 → 77.91 | 92.16 → 85.41 |
| ×3 | 56 | 64.78 → 62.76 | 85.67 → 87.51 | 87.95 → 92.52 |

The CPU replay loop including latch/analysis callbacks and the scheduler at 28 FPS averaged about 78 → 84 ns per tick at 60 Hz and 82 → 90 ns at 90 Hz (median of four runs per build on this host). These timings cannot establish Steam Deck power, GPU frametime or input latency. Phase-dependent texture sampling still varies even with identical shader binaries.

Install the inner GFG ZIP through Decky, choose Reinstall Gamescope in Setup, then restart the Deck. The standalone Kedavra ZIP is an alternative for standalone installations. Repeat the procedure with the matching contour.1 ZIP for rollback. Use a repeatable pan, the same cap, power profile and graphics settings. Compare locked 30 FPS against a 27–29 FPS sequence at both refresh rates. Record the existing pacing trace in each run and compare missed refreshes, real-frame order and P95/P99 flip intervals. A physical input-to-display measurement is still required.

## Reproduce

The engine CI checks out contour.1 alongside the candidate, compiles the same phase_trace.c against each scheduler and executes check_phase_balance.py. The logs include every measured scenario. [Engine source and CI](https://github.com/wavessevaw/GSF_Kedavra/actions/runs/45924000381)

For the rendered comparison, use a scratch directory with the candidate engine checked out as src. Build with make -C src/kedavra, configure a Vulkan ICD and install the normal C/Vulkan build tools, Python, NumPy and Pillow. Run the following from that directory with the GFG repository at GFG_PATH. The scripts instrument a local copy of the offline harness. Keep at least 1.3 GB free for the PPM output.

```sh
python "$GFG_PATH/docs/phase-balance/pair_replay.py" src/kedavra .
python "$GFG_PATH/docs/phase-balance/contours.py" pixels-old pixels-new
python "$GFG_PATH/docs/phase-balance/time_phase.py"
KFG_HARD_X2=1 KFG_COURTYARD_TIMING=1 ./timed --hard --size 1280x800 --scene h_courtyard_reversal --spv src/kedavra/build
```
