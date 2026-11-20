# Courtyard 4 test candidate

This GFG build carries the complete Courtyard 3 plugin and the Kedavra engine at 8c4e86c. The runtime evaluates a bounded curved trajectory for camera-following surfaces during a sustained change in camera velocity. It uses the two real source intervals for each velocity comparison, requires two successive changes to agree, and rejects camera estimates whose forward and backward directions disagree. A single RGBA16F texel per pair carries the result. Synthesis applies at most six analysis pixels of correction and reduces it on independent motion. Cuts, gaps and HDR bypass the correction. The scheduler and display cadence use the Courtyard 3 implementation.

Repair now leaves the side preference of the shared motion field phase-neutral. In isolation the effect was tiny. Rechecking more endpoints on disputed steady-rate edges was also tested separately. The largest repeatable improvement came from the camera trajectory. A trial that applied acceleration after a single change improved the smooth reversal but regressed when the speed snapped at exactly a real frame. The candidate requires agreement across adjacent changes.

## Results at 1280×800

Fraction of 4×4 tiles with mean absolute luminance error above 48/255; lower is better. These rows follow the forward playback order. See phase-comparison.json for the reverse order and the two sides of the grille at each intermediate phase.

| Route | Mode | Courtyard 3 | Courtyard 4 | Worst frame before → after |
|---|---:|---:|---:|---:|
| Smooth reversal, irregular source | x3 | 4.464% | 3.436% | 10.588% → 6.495% |
| Smooth reversal, irregular source | x2 | 4.740% | 3.749% | 11.917% → 7.714% |
| Smooth reversal, even source clock | x3 | 3.222% | 2.498% | 5.323% → 4.803% |
| One-direction turn, irregular source | x3 | 1.1103% | 1.1100% | 2.7094% → 2.7094% |

On the irregular reversal, forward x3 neighborhood-relative 8×8 outlier rate increased from 13.238% to 13.286%. Severe4 and neighborhood-relative outliers measure different errors. The opaque crosshair's worst-frame RGB errors remained 8.35 and 7.06 out of 255 on the two x3 phases.

## Read the measurements

The comparison video contains 8× slowed software Vulkan output and the analytic 3D reference. All quality measurements use true rendered intermediate phases. For the forward/backward matrix, every source frame and complementary phase was hashed and matched in both directions (29 images per scene and cadence). The stencil measures RGB error at screen locations that change between the fully opaque grille colour and other colours. It includes mixed edge coverage in the latter class. It is specific to this fixture.

The phase-comparison file covers the direct and reversing routes at two resolutions with even or uneven delivery. The controls include an instantaneous change in direction and an instantaneous stop, plus the existing 320×200 hard scenes. In experiments.json, neutral isolates phase-neutral repair, kinematic is steady-rate endpoint re-evaluation, visibility retains strong one-sided weights, both combines those two trials, curved is the initial camera model, production uses a relative change gate, and consistent is the delivered shader. Comparisons against the package use the same harness with Courtyard 3 SPIR-V.

The two repeated warm measurements in software-vulkan-timing.json use the 1280×800 variable reversing route in base–candidate–candidate–base order with x3. The benchmark's reduce label sums the entire analysis plan per pair; warp is per generated output. The first two pairs are excluded. The analysis medians were 163.22 and 169.89 ms. Warp medians were 47.67 and 47.67 ms; warp P95 was 56.34 and 60.27 ms. The sample is small (10 analysis and 20 warp observations per version). These timings describe llvmpipe. Steam Deck GPU time, power, physical latency and real-game quality remain unverified.

## Reproduce

Build Kedavra at 8c4e86c with make -C kedavra all. With NumPy and Pillow installed, run the command below and repeat with Courtyard 3 SPIR-V in --spv. Use --regular to select the steady source clock (33/34 ms), and --control snap or --control stop for the two abrupt-change tests.

```sh
python3 kedavra/tools/courtyard/phase_compare.py --exe kedavra/build/kfg_vktest --spv kedavra/build --size 1280x800 --scene h_courtyard_reversal --out result.json
```

## Install and roll back

Extract the Actions download once. In Decky install the enclosed GFG ZIP, open GFG Setup, reinstall Gamescope and restart the Deck. Verify runtime kedavra-1.7.0-8c4e86c. Compare the same repeatable turn at 60 Hz x2 and 90 Hz x3, inspect the background as fence edges appear and disappear, then stop the camera abruptly. Check the HUD, native frame rate, repeated displays and compositor P95/P99 at the same power limit. For rollback use the Courtyard 3 or official 3.5.0 ZIP, reinstall its Gamescope in Setup and restart.
