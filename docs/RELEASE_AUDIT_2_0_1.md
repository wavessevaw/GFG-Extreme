# GFG Extreme 2.0.1 audit

## Source evidence

- Baseline main: `e66164cd4bd163cee4db6b8bee3950106f699311`, package 2.0.0.
- Field evidence: branch `diagnostics/autopilot-2.0.0-20261011-230354`, commit `c3bd63e`, files `docs/field-logs/20261011-230354/summary.txt` and `autopilot-skipped.jsonl`.
- Baseline CI: https://github.com/wavessevaw/GFG-Extreme/actions/runs/38137130974 -- 1,052 backend tests (one skipped), native mock Vulkan integration and 91 frontend screens passed.

The diagnostics branch contains an unmodified exported summary and 15 verbatim event fields. It does not contain the entire source recording, raw renderer timeline or per-second sensors. Statements below are limited to that extract; numerical performance improvements cannot be inferred from it.

## Observed session

2,184 samples / 2,206.3 seconds. Real FPS median 29.999, p5 29.496; output median 89.993, p5 79.417. Six mode switches. TDP 8--20 W, maximum recorded temperature 74 C. Seven distinct requested operating points failed confirmation/trial; the summary reports measured cadence beside requested cadence. Many higher-real-cadence points did not sustain their target.

All 15 shading events were skipped: four without a confirmed point, three with unstable renderer cadence, eight overlapping a transition. No applied shading or GPU-clock experiment appears in the reported event counters. The current planner proposes those tools only when output is below 92% of target; admission requires at least 95%, proving an unreachable path independently of the summary. Stable high CPU/GPU load is now eligible for a proposal, while the recorded bad windows still fail admission.

Frame OS reports 12,134 layer frames and p50/p95 present interval 33.33/33.39 ms. Boost (786 samples) and calm (1,138 samples) both have 30 real FPS; present hold is 20.29 ms. This is evidence of no demonstrated real-cadence boost in that session, not an input-to-photon measurement. Existing continuous-failure backoff resets between short bursts, and Act retains the adaptive point even during boost backoff. The fix accounts for repeated failed burst exposure after interval-ring settling and temporarily returns the executor to Governor during backoff. It does not establish a hardware gain.

The game rendered at 1280x800 despite the offered 852x532 extent. The renderer explicitly reports `application-extent-override-no-source-presentation-split`; game-controlled resolution cannot be fixed by repeating Governor scale trials. The recorded CPU cap was released twice when real cadence was short. The archive summary counts 369 `acquire-generated-image` operations, but does not provide their results; a timeout count or cause cannot be established from those counters alone.

## Additional reproducible code defects

- Complete repeated samples bypassed the arbiter timeout and heat check. The outer stale/low-sample gate also bypassed the arbiter entirely.
- A no-op GPU restore erased a failed shading restore's arbiter lock. Other modes did not honor pending GPU/VRS restoration.
- A recovered GPU receipt retained an experiment with no comparison state. Restore retries could overwrite a later QAM manual override.
- A SteamOS manual frequency selected from maximum-minus-100 could exceed the actually observed GPU frequency, opposite to the intended intervention.
- GPU/VRS admission did not exclude an active Flow, CPU cap or Act executor.
- Target selection happened before the Steam-menu pause, allowing menu-contaminated windows to lower the FPS goal.
- Failed/rejected resource trials froze the budget instead of handing it back. UI could propose another tool while reporting a finished verification.

## Regression coverage

`tests/test_autopilot_release_regressions.py` tests stable actuator admission end to end, all 15 recorded skip fields, silent/repeated/overlapping/nonfinite measurements, heat, restore locks across modes, QAM override during retry, measured-clock step, Flow exclusion, menu goals, rejected-trial power availability, short-burst backoff and Act point release.

The original Linux test suite exercises Battery, Balanced, Quality, power/renderer ownership, replay, Frame OS, HUD and packaging. Local Windows runs pass the new control-path regressions; POSIX file-mode/sysfs/Vulkan validation is delegated to the existing unmodified Linux CI and release workflow. No physical Deck was available during this audit.

Publication uses the existing main-only release workflow after review CI passes. It repeats backend/native/frontend checks and verifies archive version, CRC, native payloads and checksums before creating the official release.
