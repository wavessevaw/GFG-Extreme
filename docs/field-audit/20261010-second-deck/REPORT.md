# Second Steam Deck field run: Autopilot 1.7.1 (2026-10-10)

**Verdict: RENDERER + LEGACY GOVERNOR OBSERVED; AUTOPILOT A/B/A NOT STARTED. Release gate remains BLOCKED.**

This is a **real device** log, unlike the earlier synthetic GitHub Actions suite. The raw ZIP is *not* committed to this public repository because it contains user paths, launcher configuration, game/process IDs and other environment details. Sanitized numerical time series are supplied separately to the owner. The public evidence is this report and `field-evidence-sanitized.json`.

## Source integrity

- User-provided archive: `GFG-Extreme-log-20261010-232030.zip`, **119,298 bytes**, original SHA-256 `efc5920c9457508185f4a107dfe7695768f81864395bb6dc8b4a70150bbb207d`.
- Time: 2026-10-10, **23:12:55–23:20:30 (UTC+10)**, duration **454.89 seconds**.
- Steam Deck **OLED / Galileo**, SteamOS **3.8.28**, Linux `6.18.50-valve2`; recorder reports **GFG Extreme 1.7.1 pre-alpha**.
- Corresponding public pre-alpha release: [v1.7.1](https://github.com/wavessevaw/GFG-Extreme/releases/tag/v1.7.1), tagged to `67fb4dc583da9acc214d9070b27b347c2847dc72`. Do not confuse this separate release source with the **1.6.9-era source** underlying draft PR #114/#115.
- **17/17 setup checks passed.** ZIP contains 451 1 Hz state records (+ start/stop), 966 valid Autopilot trace JSONL records, 228 renderer-diagnostics lines and 21 in-window Governor events. Trace failure counter remained zero.

## Compared to the first hardware capture

| Measurement | First capture, v1.7.0 | Second capture, v1.7.1 |
| --- | --- | --- |
| Duration | ~166 sec | **454.89 sec** |
| Real renderer diagnostic plans | **0 FPS-bearing** | **74 fixed + 58 adaptive** |
| Governor state | 166/166 DISABLED | **221 OBSERVE_ONLY**, 54 PAUSED; also normal Governor PROBE/APPLY/LOCKED/GUARD after switching to Balanced |
| Autopilot observation ticks | 163 | **439** |
| C1 measured real FPS in trace | 0 | **0** |
| C1 output FPS in trace | 0 | **34 observation ticks** |
| C2 decisions | 163 OBSERVE | **439 OBSERVE** |
| Autopilot power actions | 163 HOLD, 0 writes | **263 HOLD, 0 writes** |
| Autopilot A/B/A trials | 0 | **0** |
| Release claim | none | **Still not a functional Autopilot pass** |

## P0 root-cause finding: FPS provenance is incompatible with the strict C1 reader

1. **The renderer DOES emit frame-generation activity now.** Raw diagnostics include 74 `fixed-plan` and 58 `adaptive-plan` operations, 34 present breakdowns, 33 present totals. The normal Governor reports **legacy median real FPS 43.536**, **median output FPS 87.941**, target 90, and chooses runtime points. This is not evidence that the independent Autopilot C1 accepted those values.
2. On **133 renderer plan lines**, the source uses `base_fps`. A `fixed-plan` also supplies `observed_output_fps`; the `adaptive-plan` lines mainly supply `target_fps` and generated count, neither of which is a measured output FPS.
3. In tagged **v1.7.1** `py_modules/gfg_plugin/autopilot/observation.py`, `ObservationStream.consume()` **explicitly refuses `base_fps`** because its measurement provenance may be derived or ambiguous. It accepts real only as `current_base_fps`, `measured_base_fps` or `instantaneous_base_fps`. Raw plans have just **one** `current_base_fps` occurrence and **zero** `measured_base_fps` occurrences (one-off diagnostic text is not sustained evidence). Output is accepted only from measured `current_output_fps`/`observed_output_fps`.
4. Accordingly, across **439 C1 observations**, `source.real_fps` is **always null**. Some 34 observations have `source.output_fps`, but never a verified independent pair; all **451** 1 Hz monitor perceptions classify primary as `UNKNOWN`. Main C2 reasons: `measured-fps-unavailable` 211, `runtime-not-observing` 139, `focus-unconfirmed-or-menu` 36, `baseline-incomplete` 29, `launch-identity-unavailable` 21 and `insufficient-evidence` 3.
5. **Correct fix is NOT to alias `base_fps` or `target_fps` to true measured real FPS.** Audit the Vulkan producer for actual measured real-present/cadence provenance and emit a dedicated validated `current_base_fps` or `measured_base_fps` field, with monotonic event seq, source timestamp/context and tests showing it is not a target/plan. Preserve fail-closed C1 and demonstrate a sustained valid A1 window from physical logs.

## Governance / actuator separation

- Power Autopilot development flag TRUE in 263 of 439 trace observations; Flow flag FALSE throughout. **All 439 C2 decisions = OBSERVE**; 263 calls to the experimental power adapter returned `HOLD/not-a-power-trial`. Scheduler and slot stayed `idle`; **no applied power step, A/B/A, Flow trial, or Autopilot rollback/ACK**.
- Normal Governor state distribution over 451 samples: **OBSERVE_ONLY 221, DISABLED 83, PAUSED 54, APPLY 49, GUARD 23, PROBE 7, LOCKED 7, OPTIMIZE_POWER 6, PLAN 1**.
- The operator switched from Autopilot to **Balanced** around 222 sec, and subsequently switched back. The **normal Governor** successfully confirmed/applied **three operating points** with **two TDP writes**: 20 W → 12 W → 13 W. One deeper-multiplier request was rejected/rolled back. On disable around 370.8 sec, Governor restored the user/host ceiling to **20 W** and ownership dropped. These are **legacy Governor** actions and must not be labeled Autopilot trials.
- Across all 451 state samples, slowPPT and fastPPT were equal: **12, 13 or 20 W**. The 83 `DISABLED` state samples reported TDP **unowned**, unlike the first physical log. The source cannot establish that the physical hardware implements Autopilot recovery correctly, as no Autopilot power write occurred.
- Game-related host readbacks: **median 43.536 real FPS; median 87.941 output FPS; temperature 44–82 °C, median 72 °C**. The stock recorder's summary notes hot/heating status for approximately half its samples. Interpret thermal conditions cautiously.
- **Frame OS reported 2510 frames and gamepad events.** Its `+29.9%` A/B statistic is labeled **historical** in the recorder, with **no new pairs in this session**. It is a pacer/freshness comparison, NOT a real input-to-display latency or current Autopilot performance result.

## Remaining diagnostic concerns and gates

1. Add measured, provenance-checked real FPS to renderer diagnostics; test paired `real/output` reception end to end. Never fake fps by multiplying the target, by using `base_fps` without verification, or by treating goals as measured gains.
2. Characterize `invalid-sample-context` (**93** 1 Hz perceptions) and focus/menu transitions with same-game renderer generation/launch; make sure sequences survive/reinitialize only when context truly changes. Continue to withhold actuation on ambiguous contexts.
3. Address the separate cold-start bootstrap limitation already documented in PR #114: valid FPS alone does **not** prove Power/Flow can claim a lease and locked point safely.
4. After evidence + bootstrap are fixed, run one **bounded, explicitly controlled physical experiment** with slow+fast PPT before/after, owner, exact A1/SETTLE/B/RESTORE/A2/VERDICT windows, verified ACK and fail-closed rollback. Capture all raw logs privately.
5. Do not label a normal Balanced Governor TDP step, historical Frame OS comparison, or diagnostic setup pass as an Autopilot A/B/A result.

**Safety verdict:** The observed fail-closed behavior is preferable to acting on untrusted telemetry. **2.0.0 / Autopilot activation remain blocked.** The physical diagnostic recorder itself is functioning and captures enough structured data to isolate the provenance issue.
