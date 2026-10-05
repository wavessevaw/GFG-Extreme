# Beta 1 build status

## Build

- Product platform: GFG Extreme v4.0.0-gfg.4
- Governor: v0.0.1 Beta.1
- Local implementation commit: `6d7baa2`
- ZIP SHA-256: `4b6e124c693c53d3dc0d9e132c1efbe8b1bd22c4dd3c16b61e7aeaae544d7e33`
- Patch SHA-256: `4ac17fdec4d3070e6c16594a1348c5f059cd049888e1ec90acb2b36c61362d48`

## Validation

- 93/93 Python unit/regression/replay/service tests pass.
- Python compileall passes.
- Compiled Decky UI passes `node --check`.
- Frontend/backend RPC parity: 37 RPCs, 0 missing backend methods.
- New RPCs: `get_governor_status`, `set_governor_enabled`.

## Binary identity

The Renderer and Flatpak payloads are unchanged from gfg.4:

- Renderer: `72ae1202f2a649f65cb75a7d1082f7aeacb7e87c8a2d6f29888343d5271c2b7c`
- Flatpak 23.08: `d74a2e53ff8f80a7f662a9ef1052557cba5fbf1a63a2fef700de75aa83c11cf5`
- Flatpak 24.08: `ae2c78242e6edd0f8c148243c4559aef78f3748f0bd50702c5257c9138f64cee`
- Flatpak 25.08: `05f30339935979e94be0d346908e7d0d4b47927a4613ef67758152250705adc0`

## Beta 1 actuation boundary

The first Beta does not automatically rewrite saved multiplier/base-cap/render-scale values. Planner recommendations are observational until the running cadence already proves the selected unscaled point. At that point Governor can optimize TDP.

This preserves gfg.4 Saved / Effective / Actual semantics and prevents runtime optimization from turning into continuous profile mutation.

## TDP safety

Governor discovers Steam Deck amdgpu fastPPT/slowPPT controls, snapshots the user's current caps as the session ceiling, never raises above that ceiling, and releases ownership if QAM/another tool changes the caps.

## UI

The home surface is Governor-first. Existing detailed gfg.4 controls remain available under Advanced Controls instead of being rendered simultaneously.

## Required hardware validation

Real Steam Deck OLED Game Mode / Gamescope / writable PPT / game integration has not been run in the build environment.