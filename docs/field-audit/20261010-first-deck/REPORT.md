# First physical Steam Deck Autopilot log: forensic review (2026-10-10)

**Result: BLOCKED / NOT A FUNCTIONAL AUTOPILOT TEST.** The trace recorder works on real hardware, but the renderer supplied **zero usable FPS receipts**. Autopilot remained OBSERVE/HOLD; no A1/B/A2, renderer ACK or new power write was exercised.

## Provenance and privacy
- User-submitted source: `GFG-Extreme-log-20261010-223112.zip` (38,594 bytes).
- **Original SHA-256:** `449c3523753792b994ef1ab2b87c26f7e5f45780ab3c5f46c2e41bb3d08f17d1`.
- Original archive contains account-adjacent launch manifests, running-process data, user file paths, wrapper command/environment and configuration. **Do NOT commit the unmodified ZIP to this public repository.**
- Source is retained in the owner's conversation, not GitHub. Evidence committed here is sanitized; compare its `source_sha256` to the original before drawing conclusions. Keep the full original privately for later device debugging.
- Captured locally **2026-10-10 22:28:26–22:31:12 (UTC+10)**; approximately 166 seconds.
- Device: Steam Deck OLED (DMI model Galileo); SteamOS **3.8.28**, kernel 6.18.50-valve2.
- **Installed plugin reports GFG Extreme 1.7.0**, whereas the audit branch PR #115 is based on the 1.6.9-era PR #114 source. No source-build hash was included. The physical program's precise commit **cannot be established**; do not claim this field result directly validates PR #114/#115 line by line.

## What the bundle demonstrates

| Evidence | Observed | Assessment |
| --- | ---: | --- |
| Setup preflight | **17/17** pass | Installation/preconditions exist; NOT proof that game renderer emits frames |
| Timeline | 166 state samples (+ start/stop markers) | Recording works end-to-end |
| Autopilot trace | 490 entries: 163 observation + 163 power-control + 163 exclusive-control + 1 session-change | Instrumentation works; no missing/corrupt JSONL entries |
| Autopilot flags | Power **true**, Flow **false**, 163 observations | Experimental power path was selected |
| Governor status | **DISABLED** / `governor-disabled` for all 166 samples | C1 is blocked at the state gate despite `enabled=true` in the same timeline |
| C1 evidence | 0 measured real FPS; 0 measured output FPS; 0 source receipt IDs | Cannot classify bottleneck or begin A/B/A |
| Blocker reasons | 18 `launch-identity-unavailable`; 145 `runtime-not-observing` | No stable live validated game context |
| C2 decisions | 163 `OBSERVE` | Fail-closed decision; no trial authorized |
| Power results | 163 `HOLD`/`not-a-power-trial`; zero `wrote:true` | No experimental power action; no test of actuator restore |
| Scheduler | `idle` throughout; baseline/ACK null | A1→B→A2 and rollback are **UNTESTED** |
| TDP readback | slowPPT 20.0 W and fastPPT 20.0 W for 166 timeline samples | No variation during capture; `owned=true` is **not** evidence of an Autopilot cap change |
| APU draw | 2.11–13.13 W, median 8.045 W | Host sensor alive |
| Temperature | 39–52 °C, median 49 °C | Host sensor alive |
| Renderer log | 136 lines; only **3** `process-identity` events; **0** FPS diagnostics | Wine/launcher/helper processes observed, but no verified game-frame producer |
| Frame OS | Layer libraries present in helper process maps, no live frame receipts in summary | Loaded library ≠ active layer recording frames; root cause still open |
| Governor events within capture | 0 | Distinct activity log did record older session states and this launch |

## Why the run stalled

1. **P0 test blocker: no renderer measurement producer.** The diagnostics file grew and reported identities for Wine helper processes and a game launcher, but not a `fixed-plan`/`adaptive-plan` with measured FPS. The game's main render process is not confirmed in the captured process sample. Investigate launch wrapper / selected Vulkan device / layer chain / actual executable and whether the foreground game ever rendered frames while recording. The optional fallback diagnostics log was absent (documented as normal).
2. **P0 control-state inconsistency.** Every 1 Hz timeline row reports `enabled:true` but `state:DISABLED`; C1 then reports `runtime-not-observing`, and C2 returns `OBSERVE`. A UI mode switch to `autopilot` was recorded as successful before the capture, yet the audited Python source's `GovernorService.MODES` has only `budget/balanced/quality/extreme`. That is a **code/build parity problem**, not permission to bypass C1. Diagnose real build SHA, active Governor settings, flags and validated runtime-state transitions. Do not claim this proves one particular source line is broken without matching the 1.7.0 build.
3. **Power ownership needs a separate review.** The trace reports power lease `owned=true` and both PPT readbacks 20 W while Governor is `DISABLED`. The activity journal shows a TDP claim **before** recording began. No modification or restoration was observed during this capture; ownership origin and expected lifetime cannot be concluded without the previous private log and the active 1.7.0 code. Verify in the next capture whether a DISABLED controller is allowed to retain ownership.
4. **Frame OS report is not enough to diagnose game-frame failure.** The process inventory found the pacer/HUD/renderer .so files mapped in auxiliary processes. Summary states the layer did not report live frames. Distinguish `Vulkan layer loaded`, `actual game process running`, `present hooks active`, `diagnostics fixed/adaptive receipts` and `MangoHud FPS`.

## Log integrity / privacy observations

- All 490 trace JSONL events parse successfully, no `trace_failures`; meta reports 327,657 trace bytes and start offset 195,491; trace was present before Record, and exporter correctly included only the new recording range.
- The normal event file `governor-events.jsonl` is empty; this must not be interpreted as absence of past activity. `activity.jsonl` has 45 entries including pre-recording launch/UI/session history.
- The log recorder included the launcher script, Saved profile, plugin version, checks, power sensors and environment. **Sensitive context is why only sanitized evidence is suitable for this public repo.**
- Some Wine `ld.so` ELFCLASS32 messages and a MangoHud blacklist line appear; those lines alone are **not proof** of a fatal Vulkan/rendering error.

## Next acceptance gates (in order)

1. Record the exact **installed 1.7.0 git/build SHA**, actual `set_governor_mode` response and Governor effective profile/state. Restore consistency: when flags are armed, C1 should use an explicit `OBSERVE_ONLY`/read-only state, not misleading `DISABLED`; preserve fail-closed behavior.
2. Start a game and capture a few genuine renderer diagnostic `fixed-plan`/`adaptive-plan` events with **measured** `current_base_fps`/`current_output_fps` and fresh sequence IDs. Confirm the main game process and Vulkan layer, not only launcher helpers.
3. Verify 5+ independent source samples over 6+ seconds, correct launch/focus/generation, no repeat-counted receipts, C1 primary not UNKNOWN, C2 explicitly shows why it holds or trials.
4. Only after review of the **new source build** and safety transitions, consider a controlled trial with pre- and post- readings of **both** PPT caps, rollback ACK and full A1/B/A2 evidence. Do not forcibly enable flags solely to get a green result.
5. Capture complete startup + game entry + real frames + menu/focus + exit + post-exit restoration with `autopilot-trace.jsonl`, `timeline.jsonl`, `activity.jsonl`, renderer diagnostics and `power-sensors.json`; preserve the original privately.

**Release verdict:** This is the first successful real-device *telemetry collection*, **not** a successful Autopilot control test. Keep PR #115 draft and the production 2.0.0 gate closed until genuine FPS evidence and physical restore verification exist.
