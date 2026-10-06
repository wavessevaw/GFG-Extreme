## GFG Extreme 1.0.0

**The first official release.** Frame generation that manages itself on Steam Deck: press **Run**, and GFG picks the frame rate for your screen, decides how many frames to generate and sets the TDP as low as the game allows — then keeps adjusting while you play.

### What it does
- **Knows your screen.** Steam Deck OLED → 90 FPS, LCD → 60 FPS, dock or external display → 60 FPS.
- **Three modes.** **Battery** (lowest power first, 9–11 W ideal, at least 24 real frames), **Balanced** (at least 30 real frames, never above the Deck's normal power range) and **Quality** (fewest generated frames first).
- **Adapts all session.** Frame rate is checked every second; a starved game gets watts back in about 2 s, and one watt less is tried every 45 s while the game holds.
- **Checks every change** on the renderer's own data and rolls back what does not hold. It reads how many generated frames the renderer can produce and never asks for more.
- **Remembers your games**, so the next session starts from what worked.
- **Sees the machine:** temperature, GPU and CPU load, frame-time spikes, battery draw, and a one-line verdict of what limits the game.
- **Leaves your settings alone.** The saved profile is never modified; Stop puts everything back. No overclocking, never above your Deck's power ceiling.
- **In-game overlay** with frames on screen, multiplier, real frames, TDP and measured APU draw, battery time and effort.
- **Check setup** and **Record a log** (Settings → Diagnostics) for when something does not work; the log carries a plain-language verdict.

### Since 0.0.19
- Review follow-ups: a point inferred from delivered FPS stops being marked *verifying* as soon as the Governor leaves it (so diagnostics and game memory stay correct); the renderer's generated-frame capacity is treated as the *current* swapchain's limit, re-read every step, and a report of 0 (native only) is honoured.
- Release packaging: official versions are published as releases (not pre-releases), the version is shown at the bottom of Settings.

### Tested
On a Steam Deck OLED in real play (The Witcher 3): Battery holds **90 FPS at 30 real frames and 10–11 W**, Balanced **90 FPS at 13 W**. Every fix since 0.0.17 comes from logs recorded on a real Deck. Steam Deck LCD, docked play and other games have had less real-world testing — logs are welcome (Settings → Diagnostics → Record a log, then open an issue with the zip).

### Install
1. Download `GFG-Extreme-v1_0_0.zip` below and install it through Decky Loader (*Install from zip*). Accept the root access request — it is used only to set TDP.
2. Open GFG Extreme and tap **Install engine**.
3. In Steam, set the game's launch option to `/home/deck/.local/bin/gfg %command%` (GFG shows it with a **Copy** button).
4. Start the game and press **Run**.

Updating from a 0.0.x pre-release: install the zip over it; settings, profiles and game memory are kept.

### Verify your download
SHA-256 of the zip: `<sha256>` (see `SHA256SUMS.txt`).

### Known limitations
[docs/GFG_GOVERNOR_KNOWN_LIMITATIONS.md](https://github.com/wavessevaw/GFG-Extreme/blob/main/docs/GFG_GOVERNOR_KNOWN_LIMITATIONS.md). In short: a fractional ratio the GPU cannot feed still costs one 25 s confirmation (output stays at the target meanwhile), and an overlay change while playing is applied within 5 s.

GFG Extreme continues the MAKO and lsfg-vk work and does not contain or distribute Lossless Scaling.
