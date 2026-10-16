# GFG Extreme 2.1.5 — Governor emergency quality recovery

## Fixes
- Corrected a Governor deadlock observed on Steam Deck OLED 2.1.4: the emergency `23x3.913` point could persist for more than eight minutes while output remained near 90 FPS but real rendering stayed near 22.5 FPS.
- When running a deep emergency multiplier (above ×3), a bounded quality-recovery probe may now try the normal 30-real-FPS ×3 point directly. Previously rejected intermediate ratios (24×3.75, 26×3.5, 28×3.25) no longer block that recovery path.
- Recovery respects thermal limits, point rejection and known-failure cooldowns, and restores the previous emergency point if a quality probe fails.
- When separately measured known-good power headroom exists for the normal cadence, the Governor restores and validates that TDP before testing the harder rendering point; it does not change the point and hardware power limit simultaneously.

## Verification
- Six new deterministic regression cases cover rejected intermediate ratios, cooldown, rollback, thermal limits, staged known-good watt recovery, and preservation of the normal watts-first policy.
- CI, Temporal Engine and Frame Fusion tests are required to pass on the 2.1.5 release source.
- The release archive is checked for synchronized version metadata, native payloads, CRC and packaging integrity before publication.

## Notes and limitations
- Built on 2.1.4's fixes for unintended Auto 90→45 FPS target fallback and conflicting Frame OS Act hardware-TDP offsets.
- A recovery *attempt* is not proof that a game can achieve 30 real FPS in the same scene. Hardware effects on latency, power and smoothness have not yet been validated for this patch.
- GFG's existing supported generator setup still requires Lossless Scaling. The experimental independent GSF engine is not part of this Governor patch release.
- Steam Deck telemetry and renderer Output FPS alone are not proof of distinct frames physically presented on the display.
