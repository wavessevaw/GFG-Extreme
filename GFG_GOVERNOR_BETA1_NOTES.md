# GFG Extreme + Governor v0.0.1 Beta.1

## First working Governor build

This build is based on the exact GFG Extreme v4.0.0-gfg.4 release tree and retains its renderer/Flatpak payloads unchanged.

### Implemented

- centralized incremental renderer `TelemetryObserver` with fresh-evidence sequence semantics;
- P1/P5/median/MAD cadence statistics;
- deterministic OLED 90 / Dock 60 Operating Point planner limited to x1/x2/x3;
- coarse-to-fine non-oscillating TDP search;
- ownership-aware Steam Deck fastPPT/slowPPT actuator that never raises above the user's claimed session ceiling and pauses on external QAM/plugin changes;
- per-profile opt-in Governor runtime service and RPC;
- `DISABLED / PROBE / PLAN / OPTIMIZE_POWER / LOCKED / GUARD / OBSERVE_ONLY / PAUSED` states;
- offline JSONL replay runner and synthetic replay sessions;
- Governor-first Decky home card; prior detailed controls are retained behind `Advanced Controls`;
- structured bounded Governor event journal under runtime-state.

### Deliberate Beta boundary

Beta.1 does not automatically rewrite saved multiplier, base cap or render scale. The Planner can recommend a different Operating Point, but automatic power optimization begins only if fresh runtime telemetry proves that the game already matches the selected unscaled point. This prevents the runtime Governor from mutating the user's saved profile and preserves gfg.4's Saved / Effective / Actual model.

### Safety

Governor is disabled by default for every profile. TDP automation requires discovered writable amdgpu fastPPT/slowPPT caps. The cap values present when Governor claims the device become the hard session ceiling. Clean disable/unload restores them only if Governor still owns the values.

### Validation

Live Steam Deck Game Mode validation remains required. This package has been validated offline/unit/replay only.
