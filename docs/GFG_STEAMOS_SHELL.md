# GFG SteamOS appearance — 2.2.0 preview

Settings → GFG theme → **GFG SteamOS** enables the built-in appearance. **Restore Steam appearance** removes it. CSS Loader is not required. Disable any previously installed GFG CSS Loader theme before using this module to avoid overlapping styles.

Black surfaces, red accents, rounded cards and visible gamepad focus cover Home, Library, game details, Quick Access, Settings, Downloads, Steam menu and keyboard. Steam retains its native layout, buttons, actions and navigation. This preview implements the visual language of the approved concepts; it does not replace Steam with the mockup's custom page layouts or add mockup-only controls.

## Connection and recovery

The backend uses Decky's local Steam CEF debugging endpoint on port 8080. It accepts only Steam Gaming Mode targets on steamloopback.host and local debugging sockets. The frontend can request a boolean preference; it cannot supply scripts, URLs or styles. No Steam installation files or startup files are changed.

An idempotent heartbeat runs every three seconds while enabled. Each window receives the bundled stylesheet and a 15-second lease. Unloading the plugin removes the style. If the backend or connection disappears, the browser removes it when the lease expires (a suspended JavaScript event loop must resume first). Reloaded windows reconnect automatically. An unavailable Steam target produces a waiting state, not a false success. The enabled preference survives plugin restarts; it defaults off for this preview.

## Verification and limits

Python tests exercise preferences, lifecycle, endpoint restrictions, offline recovery and failure handling. Chromium tests exercise the actual runtime and stylesheet on eight synthetic screen fixtures: enable/restore, reload, lease expiry, focus and preserved actions. These fixtures are not captured Steam DOM and do not establish compatibility with a particular Steam Stable or Beta build. Surface detection reports matching module names, not pixel-perfect coverage.

No configured Steam Deck SSH connection was available on the development host. Physical SteamOS verification remains required: open all eight screens, navigate with the controller, test the on-screen keyboard, launch/exit a game, restart Steam, disable the appearance and confirm full restoration. Current Steam module selectors may need adjustment after that check.

## Installation

Download the `GFG-Extreme-2.2.0-shell-candidate` artifact from the candidate workflow, extract it, and install the inner `GFG-Extreme-v2_2_0.zip` through Decky's install-from-ZIP option. `SHA256SUMS.txt` identifies that ZIP. This is a candidate, not a replacement for stable 2.1.1.
