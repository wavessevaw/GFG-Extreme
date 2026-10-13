# GFG SteamOS appearance — 2.2.0 preview

Settings → GFG theme → **GFG SteamOS** enables the built-in appearance. **Restore Steam appearance** removes it. CSS Loader is not required. Disable any previously installed GFG CSS Loader theme before using this module to avoid overlapping styles.

Black surfaces, red accents, rounded cards and visible gamepad focus cover Home, Library, game details, Quick Access, Settings, Downloads, Steam menu and keyboard. Steam retains its native layout, buttons, actions and navigation. This preview implements the visual language of the approved concepts; it does not replace Steam with the mockup's custom page layouts or add mockup-only controls.

## Connection and recovery

The backend uses Decky's local Steam CEF debugging endpoint on port 8080. It accepts only carefully verified Gaming Mode CEF targets (steamloopback.host shared context or Steam native Big Picture/overlay about:blank windows) and local debugging sockets. The frontend can request a boolean preference; it cannot supply scripts, URLs or styles. No Steam installation files or startup files are changed.

An idempotent heartbeat runs every three seconds while enabled. Each window receives the bundled stylesheet and a 15-second lease. Unloading the plugin removes the style. If the backend or connection disappears, the browser removes it when the lease expires (a suspended JavaScript event loop must resume first). Reloaded windows reconnect automatically. An unavailable Steam target produces a waiting state, not a false success. The enabled preference survives plugin restarts; it defaults off for this preview.

## Verification and limits

Python tests exercise preferences, lifecycle, endpoint restrictions, offline recovery and failure handling. Chromium tests exercise the actual runtime and stylesheet on eight synthetic screen fixtures: enable/restore, reload, lease expiry, focus and preserved actions. These fixtures are not captured Steam DOM and do not establish compatibility with a particular Steam Stable or Beta build. Surface detection reports matching module names, not pixel-perfect coverage.

No configured Steam Deck SSH connection was available on the development host. Physical SteamOS verification remains required: open all eight screens, navigate with the controller, test the on-screen keyboard, launch/exit a game, restart Steam, disable the appearance and confirm full restoration. Current Steam module selectors may need adjustment after that check.

## Installation

Download the `GFG-Extreme-2.2.0-shell-candidate` artifact from the candidate workflow, extract it, and install the inner `GFG-Extreme-v2_2_0.zip` through Decky's install-from-ZIP option. `SHA256SUMS.txt` identifies that ZIP. This is a candidate, not a replacement for stable 2.1.1.


## Connection correction — shell-fix-2

The initial candidate could stay in Waiting for Steam Gaming Mode because its target-name filter omitted SharedJSContext and other names supported by Decky. Discovery now uses the local browser CDP endpoint and attaches directly to matching targets, with a legacy per-page fallback. Both transports restrict host, port and target origin. Runtime DOM checks still decide whether a window contains a supported Steam surface.

Waiting now distinguishes no matching window, a connected but unsupported document, and connection failure. State changes are recorded in the plugin log. The appearance page identifies this build as `shell-fix-2`. Real HTTP/WebSocket integration tests cover browser target discovery, flattened-session attachment, per-page fallback and rejection of a remote debugging URL. Hardware validation remains pending; this correction does not assert the user's exact failure has been confirmed from device logs.


## Connection correction — shell-fix-3

Physical Steam Deck CEF targets include the visible `Steam Big Picture Mode` window at
`about:blank?createflags=…` and `QuickAccess_uid*` / `MainMenu_uid*` popups at
`about:blank?browserviewpopup=…`. The shell-fix-2 URL restriction incorrectly
excluded these windows. The backend now admits them only with known Steam window
titles and matching internal URL query flags; all external pages remain excluded.
The runtime separately authorizes these narrow native document shapes using a
backend-assigned target role, while keeping `steamloopback.host` shared-context
support. Failure messages include the discovered target count/titles and DOM
node count for unsupported surfaces. Synthetic tests now include native URL
shapes; physical device validation is still required. This remains a candidate.


## Connection correction — shell-fix-4

Real device evidence on 2026-10-13: the backend did connect and execute the
runtime across CEF documents containing 1153, 597, 74 and 5 DOM nodes, but every
window returned `waiting-for-supported-surface`. The module-class probes were
a premature hard gate, not proof that the native Steam UI was absent.

Known, strictly title/URL-verified Big Picture and overlay CEF windows with
at least 40 DOM nodes can now receive the bundled CSS even when no known module
selector is present. A shared context still requires an explicit Steam UI
marker; sparse/empty windows, external websites and unverified CEF targets do
not receive styling. The stylesheet now includes scoped native-role canvas and
Steam dialog/tab fallbacks. The frontend reports `shell-fix-4`, and target
diagnostics include the role and applied strategy (module-probe vs fallback).

Automated Playwright checks reproduce hash-free 1153-node native DOMs, assert
a visible canvas color change, check safe restoration, overlay transparency,
shared-context rejection and sparse-window rejection. Native device appearance
still needs physical verification; an injected stylesheet is not proof that
every Steam screen matches the mockups.


## Connection correction — shell-fix-5

Physical shell-fix-4 evidence: the backend recognized `main`, two `overlay`, and
`shared` CEF targets but rejected 1153/598/74/5-node DOM documents as
`waiting-for-supported-surface`. The old fallback required the **live**
JavaScript document to be `about:blank`; this need not match the initial CDP
target URL. The actual Steam UI can be executing at `steamloopback.host`.

An already title/URL-verified `main` or `overlay` target can now use the
CSS-module-independent fallback on either a matching native `about:blank`
document or a live `steamloopback.host` document with at least 40 DOM nodes.
Only recognized Steam targets receive an enable script; remote origins, sparse
startup pages, and unknown/empty shared contexts are still refused.
The live document's verified role controls the root styling and main-page
canvas, regardless of its current internal URL.

Added a Chromium regression test that models the exact previously untested
condition: a verified native Steam target running its document from
`steamloopback.host` with 1153 DOM nodes and no recognized CSS-module
classes. The test asserts application, role, visible canvas change, and
restoration. This candidate still requires real-device visual validation.
