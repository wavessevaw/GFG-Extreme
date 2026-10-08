## GFG Extreme 1.2.0: meet Frame OS, and a HUD made of rings

Until now GFG picked a setting and held it. Frame OS goes a level deeper: a small layer sits next to the frame generator, sees every real frame and every stick flick, and decides moment to moment what the game should spend its frames and watts on.

### Frame OS (experimental) — Settings → Diagnostics
- **Fight harder, see it sooner.** Turn the camera or start a fight and Frame OS asks for more real frames (×3 → ×2) when the GPU can deliver them.
- **Real frames arrive just in time.** Act paces each real frame to the moment it is shown, so it waits far less inside the frame generator (on a Deck: about 25 ms → 13 ms).
- **Pauses pay for action.** Menus, cutscenes and AFK run at a lower cap; open Steam's menu and it rests at once.
- **It knows when it isn't helping.** A boost that brings no extra frames is not paid for again, and heat or a dip hands control straight back to the Governor.
- **You see the payoff.** A new card on Home shows three rings for this session (Response, Frames, Energy): green when it pays off, orange when it barely does, red if it made things worse.
- Start with **Observe** (measures only, changes nothing). **Act** is behind a two-tap unlock.

### Rings in your game — Settings → In-game overlay → Rings
- The text line in the corner becomes the Home screen in miniature: a brand-red FPS ring with your real frame rate, TDP, battery, and the Frame OS rings coloured by how much they pay off.
- **No flicker.** Every ring shows a 20-second average and refreshes every 20 s: one glance, the honest picture.
- Drawn by GFG's own tiny Vulkan layer after the frame generator. Pick Rings once, restart the game, done; the classic text line is still one tap away.

### The Governor got sharper
- Remembers what it learned when you switch between Battery and Balanced; a per-game reset sits in Diagnostics
- Pauses its measurements while Steam's menu is open, so a menu no longer looks like a failing setting
- Follows a lower screen refresh rate (an OLED at 60 Hz targets 60)
- **Last session in rings:** when the game closes, Home shows the session's average FPS, real frames and TDP, plus the Frame OS payoff, with the modes you played in and the energy saved, measured from real power draw
- Effort shows its reason, e.g. `HARD · x3 required`
- Bug fixes and improvements

### Install
Download `GFG-Extreme-v1_2_0.zip` below and install it through Decky Loader (*Install from zip*) over your current version; settings and profiles are kept.

### Verify your download
SHA-256 of the zip: `<sha256>` (see `SHA256SUMS.txt`).
