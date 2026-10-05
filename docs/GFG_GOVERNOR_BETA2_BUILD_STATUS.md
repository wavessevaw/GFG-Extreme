# Governor v0.0.1 Beta.2

Beta.2 addresses the two first-Deck findings from Beta.1:

1. **Telemetry was not actually enabled.** Beta.1 had a TelemetryObserver but the managed wrapper defaulted `MAKO_PRESENT_DIAGNOSTICS=0`. Beta.2 adds a runtime marker (`runtime-state/governor-diagnostics.enabled`) managed by Governor settings and bumps the wrapper format to 75. A newly launched managed game enables renderer diagnostics when the marker exists.
2. **The UI was not a real redesign.** Beta.1 only collapsed the old interface. Beta.2 replaces the installed-state information architecture.

## New UI structure

Home:
- active game / current profile
- Governor hero: target, Real → GFG → Output, TDP, state
- Frame Generation
- Scaling
- Profiles
- Advanced

Dedicated screens:
- Governor
- Frame Generation
- Scaling
- Profiles
- Advanced hub
  - Pipeline Inspector
  - Activity / Journal
  - Shaders
  - Engine Tuning
  - Compatibility
  - System

The old `FeatureSettings` aggregate is no longer rendered from `Content`, and `showAdvancedControls` is removed.

## Telemetry diagnostics

Generic `telemetry-stale-or-unavailable` was split into:
- `diagnostics-log-unavailable`
- `diagnostics-path-unavailable`
- `diagnostics-active-no-events`
- `diagnostics-events-no-fps-samples`
- `telemetry-stale`

The game must be relaunched once after Governor is enabled so the wrapper environment reaches the renderer.

## Validation

- 97/97 tests PASS
- compileall PASS
- node --check PASS
- 37/37 frontend RPCs backed
- Renderer SHA unchanged: `72ae1202f2a649f65cb75a7d1082f7aeacb7e87c8a2d6f29888343d5271c2b7c`
- Flatpak payload hashes unchanged
- ZIP SHA-256: `ab9791d17184f0f73cacfa7ae22c71a2981b8b0895d080f1510e4b0c7a5a497d`
- Patch SHA-256: `89d9f93effa1487a91e6bb34eae651dcdae143c92127d6885edf44a38d8a1bd6`
