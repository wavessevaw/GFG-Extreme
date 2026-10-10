# GFG Extreme 2.0.4 | Autopilot GPU + Half Rate Shading

Release status: **experimental prerelease; Steam Deck hardware not validated**.

This package is built from Draft PR #117 on `feature/autopilot-2.0.0`; it is **not merged to main** and is **not the latest stable release**.

## Autopilot changes

- The official SteamOSManager **GpuPerformanceLevel1** session-bus properties replace direct AMDGPU OverDrive for GPU clock trials. CPU-limited workloads can trial a small change via Steam's manual GPU clock setting, verify read-back, compare real/output FPS, CPU/GPU utilisation, frametime, temperature, and APU power, then keep or revert the trial. A user-controlled manual clock is never overwritten. If SteamOSManager is unavailable, GPU control fails closed.
- **Half Rate Shading (RADV VRS 2x2)** can be enabled as an **opt-in per-game experiment** in Autopilot. The Steam/Gamescope session's own `RADV_FORCE_VRS_CONFIG_FILE` is toggled in place, with restore receipt, and the existing arbiter evaluates fresh FPS/frametime/power samples. Unsupported games keep their original settings. The feature may noticeably blur text, HUD, and small objects.
- GPU clock and Half Rate Shading trials are serialized with one arbiter; no simultaneous experimental TDP, CPU split, Flow or GPU changes. Protective controls and rollback retain priority.
- The original Steam QAM setting and automatic mode are restored on Stop, mode switch, game exit or rollback. Source-side regression tests cover manual overrides, missing interfaces, file changes, failed and pending restores.
- Real FPS, Output FPS, GPU/CPU load percentage, APU temperature, GPU MHz, APU watts and real frametime are included in optimization decision logs. These come from the Governor's existing Linux/system and renderer telemetry, **not optical capture of the Steam performance overlay**.

## Additional 2.0.4 safety fix

- Half Rate Shading restore now verifies the exact originating Steam VRS file. A subsequent game's own Half Rate Shading choice is never overwritten by a previous session's rollback; covered by a regression test.

## Known limits and safety

- Real GPU clock writes and dynamic Half Rate Shading have **not yet been verified on Steam Deck LCD/OLED hardware**; the install is for controlled testing only. Never treat successful sysfs or D-Bus read-back as proof of frame delivery or image quality.
- The shading option is **off by default** and requires opt-in; it works only with RADV/Mesa games that actually support the SteamOS dynamic VRS config file.
- Half Rate Shading changes shader precision across rendered output, **not selectively on generated intermediate frames**.
- Experimental GPU clock changes use the SteamOSManager interface when available. On firmware without that interface, the control is unavailable and TDP optimization continues.
- The Adaptive target switch 60/90 on OLED still needs physical smoothness checks. No hardware FPS gain, latency gain or watt savings are claimed.
- Allow Tearing is **not automatically changed** by this release.

## Diagnostics

Settings → Diagnostics → Record log; stop recording to export a ZIP. Verify recovery to prior GPU and VRS settings when testing.

Do not mark this release stable or merge it to `main` without explicit authorization.

## 2.0.4 field-log hotfix — 2026-10-11 Steam Deck OLED

The supplied 15-minute diagnostic archive showed two Half Rate Shading trials
while the Steam Quick Access Menu had covered the game: 30x3 output had
temporarily collapsed to ~43 FPS, and another trial was attempted before any
point was confirmed. Both were rolled back but these were invalid comparisons.

- GPU clock and Half Rate Shading trials now require a confirmed operating
  point, a full fresh post-transition measurement window, its verified
  multiplier and near-target real/output cadence.
- A Steam menu focus event forbids new experiments; an in-progress GPU/VRS
  trial is interrupted and rolled back instead of being judged on the
  menu's incomplete renderer output.
- New regression tests reproduce the 42.674 output-FPS menu transition,
  absence of a confirmed point, insufficient post-menu evidence and
  fresh stable 30x3 eligibility.
- Ordinary Governor TDP control remains unchanged.
- Diagnostic evidence: the archive reported mode/version 2.0.1 while
  showing experimental 2.0.3-era shading actions. Software identity in
  the prior field recording is therefore mixed/unconfirmed. This release
  is separately built from its own verified commit.

No improvement in frame rate, image quality or battery life is claimed
without controlled game-device tests with the QAM closed.
