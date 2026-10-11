# GFG Extreme 2.0.0 — Deck field log, 2026-10-11 23:03:54

**Branch-only diagnostic handoff. Do not merge raw diagnostics into `main` or a release.**

## Source and transfer integrity

- Original user-uploaded archive: `GFG-Extreme-log-20261011-230354.zip`
- Archive size: **1,835,765 bytes**
- SHA-256: `ec965b6128adea73907b6f92e3e9678534480edf1c732b47aeee6f3598634212`
- Contains **16 members** (including `timeline.jsonl`, `governor-events.jsonl`, `diagnostics-present-diagnostics.log`, `self_test.json`, `system.json`, `activity.jsonl`).
- **Transfer status: full raw ZIP is NOT stored in this Git branch.** Direct upload of its complete encoded binary was blocked by a content-safety check. The files below are extracted diagnostic evidence, not a lossless replacement. Never claim that the archive is uploaded without a matching Git blob SHA-1 `43e82cff4803fad40473a59f85f16de4b5998dd5` and a SHA-256 check.
- `summary.txt`: exact untouched bytes from the ZIP's `summary.txt`, confirmed with Git blob SHA-1 `39a2c7dc765d326de5f23831ae813559668150c4`.
- `autopilot-skipped.jsonl`: all 15 skipped Half Rate Shading event records, with original field values (re-serialized as a limited subset, in original order).
- `renderer-timeouts.jsonl`: five `generated-image-timeout` diagnostics, extracted from original renderer lines 1136, 1420, 50661, 51407 and 51431.

## System and overall observations

- GFG Extreme 2.0.0; Steam Deck OLED / Galileo, SteamOS 3.8.28; 36 minutes 46 seconds; **2,184 sampled telemetry points**.
- Median **Real FPS 29.999**, Output FPS **89.993** (Output p5 **79.417**) with a 90 output goal.
- TDP observed range **8–20 W**; peak recorded temperature **74 °C**.
- Modes were switched 6 times. Most used working point: `30x3` (1,791 samples).
- Renderer diagnostics: 51,444 lines / 51,332 events; five explicit generated-image acquisition timeout/quarantine records.
- Autopilot: **1,131** `autopilot-decide` events; **15** `autopilot-actuator-skipped`, all for `half-rate-shading`. **Zero** `autopilot-shading-apply`, `autopilot-accept`, or GPU Clock application events in this archive.
- Power Split lowered the CPU clock ceiling to 3.0 GHz for some of the session; render-scale offered 852×532 but the game rendered 1280×800.
- Frame OS Act boost did not increase Real FPS over calm (both approximately 30 in this session).

## Bugs and next validation

1. **Impossible trigger/gate pair for actuator experiments.** `py_modules/gfg_plugin/autopilot/planner.py` proposes GPU Clock or shading when Output FPS is below 92% of target. `governor_service.py::_autopilot_trial_ready` requires at least 95% of target. At a 90 FPS target this means proposing below 82.8 FPS while requiring at least 85.5 FPS. The current gate blocks all such proposed experiments. Fix while keeping non-overlapping telemetry, a confirmed operating point, Quick Access Menu pause, safe ownership and rollback.
2. Investigate CPU cap delayed readback and rapid cap release without assuming a non-immediate readback means a failed write.
3. Inspect the five renderer timeouts; distinguish recovered transport quarantine from a persistent stall.
4. Examine why the separately managed Flow Scale experiments never received eligible context.
5. Validate physical Steam Deck LCD/OLED before claiming GPU-clock or Half Rate Shading effectiveness.

## Privacy and scope

The extracted material excludes raw process environment, launch wrapper and user files. The full original archive may contain local environment details and should be reviewed before publishing to a public repository. This directory is intentionally a **partial forensic extraction**, not the entire ZIP.
