# GFG Extreme Governor v0.0.1 Beta.2

## UI rewrite

Beta.2 replaces the Beta.1 installed-state Decky information architecture instead of hiding the old interface behind one Advanced toggle.

Home now contains only:
- active game/profile identity;
- Governor performance hero (target, Real -> GFG -> Output, power, state);
- routes to Governor, Frame Generation, Scaling, Profiles, and Advanced.

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

The previous `FeatureSettings` aggregate is no longer rendered by `Content`, and the `showAdvancedControls` collapse mechanism is removed.

## Telemetry fix

Beta.1 created an Observer but the generated wrapper defaulted `MAKO_PRESENT_DIAGNOSTICS=0`, so a real Deck could remain in `PAUSED` with no Real/Output FPS.

Beta.2 adds a Governor diagnostics marker:
- enabling Governor creates `runtime-state/governor-diagnostics.enabled`;
- wrapper format is bumped to 75;
- managed launches enable `MAKO_PRESENT_DIAGNOSTICS=1` only while that marker exists;
- ordinary non-Governor usage keeps diagnostics disabled by default;
- disabling the final Governor-enabled profile removes the marker.

A managed game must be relaunched after Governor is enabled so the new wrapper environment reaches the renderer.

Telemetry pause reasons are now explicit (`diagnostics-log-unavailable`, `diagnostics-active-no-events`, `diagnostics-events-no-fps-samples`, `telemetry-stale`) instead of the generic Beta.1 state-or-unavailable condition.

## Scope

Beta.2 still preserves Saved / Effective / Actual separation. It does not yet automatically persist Planner multiplier/scale choices into the user's saved profile.
