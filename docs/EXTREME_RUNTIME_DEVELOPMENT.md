# Comprehensive Extreme runtime development

Runtime foundations shipped in 1.6.5 (PR #85). Release 1.6.6 connects native frame timing and stall shield to per-profile controls and confirmed booster states (PR #86). Remaining integration work is listed below.

## Acceptance criteria

All nine boosters and existing settings/filters must remain accessible in Extreme.
Accessibility is separate from runtime support: show requested, applied, confirmed,
blocked reason and pending restoration. Never label a placeholder as active.

- Both fastPPT and slowPPT must be bounded before renderer trials; internal replans
  must keep the Extreme ceiling. Leaving Extreme restores the inherited configuration.
- A failed ceiling write must stop trials, including the observe-only fallback.
- Every system mutation needs readback, identity-scoped ownership, reversible undo,
  a bounded lease and recovery after helper/plugin restart.
- Current-session measurements must remain separate from remembered measurements.
- HUD updates must use cached snapshots; no per-frame process scans or D-Bus calls.
- Frame-generation output FPS is not real FPS or hardware input latency.
- Ghosting claims require image comparison; timing logs cannot prove image quality.

## Implemented foundations in 1.6.5

1. Bounded PPT ownership before trials and preserved ceilings across internal replans.
2. Native optional stall-shield policy and explicit support/active telemetry bits.
   Shield is opt-in per profile; frame timing preserves its existing default. Both now have controls and native acknowledgement in 1.6.6.
3. Root-helper leases for GFG-marked game thread priorities and OOM preference.
   PID/TID start times guard against identifier reuse. Undo is persisted before writes;
   expiry, EOF and helper restart restore changes if still owned.
4. OEM fan-controller interface with a persistent undo record, readback and lease.
   This selects existing firmware/OS control; it is not predictive custom cooling.
5. Regression coverage for transitions, expiry, crash recovery, external changes,
   inherited thread priority, partial failure and reused process identifiers.

Process and fan resources are not yet wired into the Governor as active boosters.
Native frame timing and stall shield are connected in 1.6.6: Home → Extreme or
Settings → Diagnostics. Act must be enabled and the updated layer loaded. Only
current-generation native acknowledgement with support/active bits counts as active.

## Remaining development

- Wire resource leases to the active game, settings and confirmed booster status.
- Implement Steam download control with verified pause/resume and persistent undo.
  Pausing downloads must not be presented as stopping all shader compilation.
- Validate native frame timing and stall recovery on the Deck; CI covers policy/status/UI integration.
- Investigate Act/FG starvation and rejected fractional operating points together.
- Add supported reverse CPU/GPU power allocation with transactional restoration.
- Make every setting/filter accessible while surfacing actual layer conflicts.
- Provide game-specific scaling fallback where source/presentation sizes cannot split.
  Ghost of Tsushima's ignored scale must remain blocked until actual extent changes.
- Implement and validate meaningful memory management; OOM preference alone is not
  CryoUtilities, swap tuning, huge pages or measured stutter reduction.
- Complete ghosting controls/history rejection and validate image quality separately.
- Run the complete backend/native/frontend/HUD CI and equal-condition Deck tests.

## Validation limits

CI can prove transitions, arithmetic, protocol compatibility and mocked driver behavior.
It cannot prove Deck fan behavior, FPS gain, actual game render resolution, input latency
or ghosting improvement. No percentage gain should be advertised without matching
current-game measurements.
