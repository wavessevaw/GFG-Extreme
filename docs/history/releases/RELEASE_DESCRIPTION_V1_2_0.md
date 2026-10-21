## GFG Extreme 1.2.0 (experimental pre-release): Frame OS and Rings HUD

Frame OS introduces a Vulkan pacer, a Governor-controlled adaptive Render v4 configuration, and controller-driven decisions. **This is an experimental build**: functional integration has host/CI tests, but end-to-end frame ratio, latency and battery improvements have not yet been established by matched Steam Deck A/B trials.

### Frame OS (experimental) — Settings → Diagnostics
- **Fight harder, see it sooner.** Turn the camera or start a fight and Frame OS asks for more real frames (×3 → ×2) when the GPU can deliver them.
- **Presentation timing (experimental).** Act attempts to pace real frames. Any reduction in input-to-photon latency is a hypothesis until independently measured; frame-age and present-hold telemetry are only proxies.
- **Pauses pay for action.** Menus, cutscenes and AFK run at a lower cap; open Steam's menu and it rests at once.
- **It knows when it isn't helping.** A boost that brings no extra frames is not paid for again, and heat or a dip hands control straight back to the Governor.
- **You see diagnostic indicators.** The Home card shows Response, Frames and Energy estimates. **These are model/proxy percentages, not verified gains versus Governor-only**: Response uses an estimated baseline and frame-age proxy; Frames compares observed real-cadence proxies; Energy compares TDP caps, not measured saved Wh.
- Start with **Observe** (measures only, changes nothing). **Act** is behind a two-tap unlock.

### Rings in your game — Settings → In-game overlay → Rings
- The text line in the corner becomes the Home screen in miniature: a brand-red FPS ring with your real frame rate, TDP, battery, and the Frame OS rings coloured by how much they pay off.
- **Calmer display.** Ring values are averaged and refreshed about every 20 s. The Frame OS benefit rings are experimental estimates, not benchmarks.
- Drawn by GFG's own tiny Vulkan layer after the frame generator. Pick Rings once, restart the game, done; the classic text line is still one tap away.

### The Governor got sharper
- Remembers what it learned when you switch between Battery and Balanced; a per-game reset sits in Diagnostics
- Pauses its measurements while Steam's menu is open, so a menu no longer looks like a failing setting
- Follows a lower screen refresh rate (an OLED at 60 Hz targets 60)
- **Last session:** on game exit, Home shows session FPS, real frames, TDP, and time spent in Frame OS states. Any modeled Frame OS benefit remains an estimate, not a measured energy saving against a matched baseline.
- Effort shows its reason, e.g. `HARD · x3 required`
- Bug fixes and improvements

### Install
**Pre-release / use at your own risk.** First use Observe or Shadow; Act requires deliberate unlocking and has not passed Steam Deck hardware validation. Rings HUD uses a 64-bit Vulkan layer and requires a game restart. Flatpak game support for Frame OS/Rings is not verified.

Download `GFG-Extreme-v1_2_0.zip` below and install it through Decky Loader (*Install from zip*) over your current version; settings and profiles are kept.

### Verify your download
SHA-256 of the zip: `<sha256>` (see `SHA256SUMS.txt`).
