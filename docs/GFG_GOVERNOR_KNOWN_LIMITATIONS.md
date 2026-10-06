# GFG Governor v0.0.1 Beta Known Limitations

1. Operating Point actuation is deliberately incomplete. Beta 1 recommends Native/45x2/30x3 or Dock equivalents, but does not automatically rewrite saved FG multiplier or render scale. Automatic TDP search runs only when actual telemetry already confirms the recommended unscaled point.
2. Renderer diagnostics are consumed from the retained diagnostics log. A dedicated shared-memory telemetry ABI was not confirmed in the current bundled Renderer v4.
3. GPU/CPU utilization, clocks, temperature and package-power telemetry are not yet normalized into the Governor snapshot. Beta decisions use renderer cadence/pressure plus the PPT actuator.
4. Automatic TDP requires writable amdgpu hwmon `fastPPT`/`slowPPT` cap controls. If unavailable, Governor stays observe-only.
5. External FG backends are observe-only. Governor never changes OptiScaler or in-game Native FG settings.
6. Native in-game FG remains opaque unless a future evidence source proves its internal state.
7. The full final UI redesign is not complete. Beta 1 introduces a sparse Governor-first home surface and moves the existing engineering controls behind `Advanced Controls`; deeper screens remain from gfg.4.
8. Live Steam Deck Game Mode hardware validation is still required. Offline/unit/replay tests cannot prove actual SteamOS permissions, renderer cadence behaviour, or game-specific stability.
