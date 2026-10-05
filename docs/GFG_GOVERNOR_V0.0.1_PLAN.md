# GFG Governor v0.0.1 Beta — Development Plan

## Non-negotiable baseline

GFG Extreme v4.0.0-gfg.4 is the host platform. Existing hardening, backend ownership, Saved/Effective/Actual, Pipeline Inspector, Config Journal and Dock protections are preserved.

## Governor principle

Observe → Prove → Choose → Optimize Power → Lock → Intervene only when necessary.

Targets:
- Steam Deck OLED: 90 output FPS.
- Dock: 60 output FPS.

Automatic operating points are deliberately small:

OLED:
1. Native 90 @ 100%
2. 45×2 @ 100%
3. 30×3 @ 100%
4. 30×3 @ 90%
5. 30×3 @ 80%
6. non-viable

Dock:
1. Native 60 @ 100%
2. 30×2 @ 100%
3. 30×2 @ 90%
4. 30×2 @ 80%
5. 20×3 degraded fallback
6. non-viable

x4/x5 are never automatic Governor choices.

## Delivery order

1. Audit gfg.4 and preserve regression contracts.
2. Telemetry capability spike.
3. Incremental TelemetryObserver.
4. Offline replay framework.
5. Capacity model (P1/P5/median/MAD).
6. Stability model (P5/MAD + misses/bypasses/pressure).
7. Deterministic Planner.
8. Coarse-to-fine Power Governor.
9. Guard + known-good TDP restore.
10. Runtime integration for GFG backend only.
11. Journal + Pipeline Inspector integration.
12. Full Decky UI redesign.
13. Synthetic replay suite + gfg.4 regression suite.

## UI reset

gfg.4 is a functional baseline, not a visual baseline. The Decky UI will be rebuilt around:
- active game
- 90/60 target
- real → multiplier → output
- current power
- Governor state

Technical controls move to contextual or Advanced screens. Existing RPC behavior is preserved.
