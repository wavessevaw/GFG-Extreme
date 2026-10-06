## GFG Extreme Decky: Governor v0.0.9 (pre-release)

**Battery mode adapts all the time: watts come back within seconds, and lower watts are tried continuously.**

> **Pre-release, not yet tested on a Steam Deck.** Please record a log (Home → Record log) in a game with the Governor on, and send it.

### Changed
- **FPS is checked every second.** If the game falls short of its real-frame cap while the APU draws all it is allowed, the Governor raises TDP within about 2 s. It does not wait for two 15 s windows. If the APU is not at its limit, more watts would not help, so nothing is raised quickly. The usual rules handle it, deeper multiplier first.
- **Back to the working level after a menu or a pause.** A paused game holds its cap at very low watts, so Battery mode walks TDP down. When the game resumes, the Governor jumps straight back to the last level the game used at its limit in the last 15 minutes. Without that history it climbs 2 W every 3 s. The fast path stops at 11 W (the ideal budget). Above that the careful rules apply: a deeper multiplier first, then 12–15 W.
- **No more "locked in".** While the game holds, Battery mode tries 1 W less every 45 s (previously every 5 min; still every 5 min without a draw sensor). A step that does not hold is undone by the per-second check, so it costs a dip of about 2–3 s. Repeated failures back off to 90, 180 and 300 s.
- **Shorter windows for lowering.** Each lower step is judged on 8 s windows (previously 15 s), two in a row.
- **Loading screens are told apart by power draw.** A collapse of real FPS with the draw far below the cap (loading screen, menu) never buys watts quickly. With the draw at the cap, the game is starved and gets them at once.
- The home screen shows **Adapting · N W** instead of **Locked in**.

Everything from v0.0.8 is included (the Governor turns on in a running game).

### Install
1. Download `GFG-Extreme-Governor-v0_0_9.zip` and install it through Decky Loader (install from zip). Accept the root access request.
2. Close the game, press **RUN**, start the game.

### Verify your download
SHA-256 of the zip: `<sha256>` (see `SHA256SUMS.txt`).

### Known limitations
See `docs/GFG_GOVERNOR_KNOWN_LIMITATIONS.md` (items 17–18). The starvation check relies on the measured APU draw. If the draw sensor reads the wrong channel, the fast path for collapsed FPS does not fire, and the game falls back to the slow rules.
