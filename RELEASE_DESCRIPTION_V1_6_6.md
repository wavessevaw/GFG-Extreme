# GFG Extreme 1.6.6

Official maintenance release based on the ordinary GFG renderer. GFG Open is retired: its generator, switch, shaders and build pipelines have been removed. Old experimental profile options are discarded and the launch wrapper is regenerated on upgrade. Restart running games after installing.

## HUD corrections
- ENERGY number shows the percentage of the device's maximum TDP allowance saved: a 20 W Gamescope/QAM maximum at a confirmed 15 W cap shows **25%**. The higher confirmed fast/slow cap is used; unknown limits show no invented saving. This is TDP headroom, not measured battery energy.
- ENERGY arc shows the console's battery charge independently of that number: green at 50% and above, transitioning towards red below 50%. Unknown charge is empty and grey.
- Charge, charging state, battery-time fallback, Frame OS measurement badges and presets are handled consistently. Current FPS replaces stale long-window values; brief missing samples expire, and game/profile changes reset the HUD.
- Cached ring rendering refreshes once per second without rerendering unchanged values.

## Extreme and frame pacing
- Includes the fixes accumulated after 1.6.5 for enforcing the inherited player/device Extreme ceiling during transitions, restoring CPU policies, rejecting unconfirmed render scales and separating current-session A/B evidence from historical results.
- Unlocks the Extreme quarter-step fractional ladder through 4x (including 3.25x, 3.5x and 3.75x), with 4x as a fallback, and the full settings/booster controls.
- Includes the native Frame OS late-frame pacing fix; the ordinary renderer remains the frame-generation backend.
- Extreme and Frame OS Act retain their experimental status. Unsupported boosters are reported as unavailable rather than claimed to be active.

## Validation
Backend regression tests, frontend smoke tests, native Frame OS/HUD integration checks and install-archive validation run before publication. Deck hardware image quality and game smoothness cannot be established by CI alone.

Install **GFG-Extreme-v1_6_6.zip** with Decky's ZIP installer. This official 1.6.6 replaces the deleted prerelease that previously used the same version. If upgrading from a numerically newer experimental build, install this ZIP explicitly.

SHA-256: `<sha256>`
