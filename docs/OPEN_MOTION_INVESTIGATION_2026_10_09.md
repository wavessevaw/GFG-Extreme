# Open motion investigation — 2026-10-09

Publication is paused at the user's explicit request. The user's Deck run of 1.6.11-test.1 still feels like 30–35 FPS despite approximately 90 output FPS. This report does not claim the field problem is resolved.

## Confirmed mechanisms

1. Earlier field recordings show GPU-guard bypass: generated outputs copy a real frame. test.1 changes guard policy and caches reference patches but does not prove actual Deck smoothness.
2. A separate content-dependent failure is reproduced with actual compiled SPIR-V, software Vulkan and validation enabled. It is outside guard bypass: timing.w=0. Both intermediate timestamps are exercised at 1/3 and 2/3. The moving texture has an exactly known horizontal translation, with history reset between cases.

Textured synthetic scene, 16-pixel tiles, central moving pixels:

| Source translation | Correct flow tiles | Wrong intermediate position at 1/3 | At 2/3 |
| --- | --- | --- | --- |
| 6 px | 35/35 | 0/6463 | 0/6463 |
| 12 px | 35/35 | 0/6372 | 0/6372 |
| 18 px | 5/35 | 5773/6464 | 5813/6464 |
| 24 px | 0/35 | 6520/6552 | 6518/6552 |

A smooth sinusoidal texture also fails at 24 px (correct flow tiles 0/35; wrong positions 6254/6580 and 6258/6580). A thin opaque object exercises static-tile and nearest-source fallbacks but per-pixel source-like counts alone are not unique-frame measurements: binary colours can coincide even in a correctly moved image.

The coarse search spans ±16 full-resolution pixels (quarter-resolution candidates ±4). Fine search is centred on the coarse proposal; the selective wide lattice also spans ±16. This explains limited displacement coverage; a ±3 fine radius around an accurate edge proposal does not guarantee an 18 px match when the coarse proposal aliases. The composer falls back to the nearest source when bidirectional confidence/consistency or colour agreement rejects a reconstruction.

These are synthetic correctness findings, not Steam Deck GPU-cost measurements or proof that every moving game pixel takes this path. The new field log must identify the loaded native version, active/bypass guard state, actual full/probe cost and presentation cadence. No search expansion should be shipped based only on these tests: raising search cost may re-trigger bypass or reduce real FPS.

## Validation

Latest investigated head: de2a1d9400cab4000cf61fd7367ec05f5dceb1cd.

- CI 37935624688: success.
- Open/native 37935624747: success, including diagnostic sweep.
- HUD audit 37935624705: success.
- Original 1.6.10 / cached shaders retain identical test output pixel hashes for both tile grids.
- HUD changes are kept in the working branch. ENERGY centre is device-relative TDP savings; arc is charge. Green at/above 50%, hue towards red below; unknown data is not fabricated.
- New releases and official merges remain held. The existing test.1 release is unchanged.

## New original Deck capture located in PR #92

Data branch: handoff/gfg-open-field-logs-20261009, commit 0db5a4e5eb4a24913ea53e48a4a7cd1238d40534.
Archive: GFG-Extreme-log-20261009-230950.zip (123,902 bytes).
SHA-256: b8f4fad63e6f5960ea1113c5b3fb2619ffe12fd3b6f9ef35fa7cf60b04a7c535.
This commit adds original field data, not source code.

Read-only evidence run 37936677718 verifies the archive hash before reading it. Recorder identity is 1.6.11-test.1. The native snapshot confirms color-flow-v2 and source-period-quarter-capped-8ms, so the new native policy was loaded.

open-performance/3957.json:
- budget_ms: 8; recovery_budget_ms: 6.
- passthrough=true; safety_latched=true; interpolation_attempted=false.
- scheduled interpolation outputs: 751; real-copy outputs: 6882 (90.16% of these scheduled outputs).
- last_active_gpu_ms: 12.77424; prepass: 11.66696; composition: 1.10728.
- probes: 6; recoveries: 2; next probe after 1402 source frames.
- current 0.25988 ms is bypass-copy cost, not interpolation cost.

Runtime events include full-work failures at 8.32596 ms against 5.55552 ms and 10.719 ms against 7.67131 ms; failed recovery probes reach 11.2034, 12.7578, 10.5297 and 12.7742 ms. The text periodic diagnostic incorrectly prints the old static 4 ms constant; the trip event and snapshot report the dynamic allowance correctly.

188 timeline samples across ~190 s include pauses, disabled Governor and transitions. Median real FPS 36.475, output 89.036; this is not proof of 89 distinct displayed motion frames. The direct field explanation remains confirmed guard bypass/copies. Prepass consumes ~91% of the last full synthesis cost; raising the bounded allowance did not solve its cost. Further work must reduce prepass cost while testing displacement coverage and avoiding new real-FPS regressions. The independently reproduced large-displacement failure remains a separate correctness issue.
