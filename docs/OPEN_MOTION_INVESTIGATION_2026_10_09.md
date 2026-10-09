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
