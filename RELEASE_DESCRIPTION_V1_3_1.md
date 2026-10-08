## GFG Extreme 1.3.1: a rock-steady HUD, smarter timing, steadier Frame OS

### The in-game rings stop flickering
- **On every frame, always.** The HUD layer used to skip the overlay on a frame whenever the GPU had not finished the previous copy yet — once a second on every overlay update, and more often under load. Each image now has two independent slots with their own staging copy, so a free one is always there; an overlay update never waits for the GPU, and the game is never stalled for it.
- **No more blinking numbers.** One late renderer sample no longer turns FPS into "—" and back; the last good values are held for a few seconds. The Frame OS rings no longer vanish for a missed telemetry beat, and a one-second probe glitch no longer swaps the rings for the text line.
- **Calmer badges.** CALM / VERIFYING / REST stay at least two seconds instead of flipping every refresh. A verified BOOST still appears and disappears exactly with its evidence.

### Predictive Presentation
The Frame OS pacer now plans each frame from the **trend** of the scene's cost, not just its recent history. When a scene gets heavier, the plan moves ahead of it instead of missing frames; when it gets lighter, the reserve is given back at once instead of two seconds later. In a scene that keeps changing weight, missed frame slots dropped from 0.5 % to zero in our simulation; on steady scenes it plans exactly as before.

### Frame OS that trusts evidence, not luck
- **Per-game decisions need real evidence.** An effect is switched off for a game only on at least 8 comparisons from at least 2 sessions, with a stricter 99 % test and a minimum harm of 2 %, and only at the start of a session. In simulation, a harmless effect is no longer switched off at all, and a real +8 % boost only in 2 % of games (both were far higher in 1.3.0). Records from 1.3.0 carry over.
- **The frames check measures the full gain.** Its settle time now covers the pacer's measurement window, so the first control samples no longer read the boost cadence.
- **The energy check fits a menu visit**, so pauses can finally be measured.

### Steam menu, done right
- A Steam menu left open no longer counts as a starved game: the Governor stays paused and Frame OS rests for the whole visit (the renderer reports focus only once, and 1.3.0 forgot it after 5 seconds). Three long menu visits no longer lock Act out for the session.
- If the "game is back" event is lost, generated frames on screen end the pause right away, and a menu event never holds for more than two minutes.

### Fixes
- The in-game badge reads `BOOST 45R x2` again (the overlay font had no lowercase x).
- A boost is no longer marked ineffective right after an A/B check or before the Act executor is in place.
- A game exit no longer counts as a new Frame OS session in the game's memory, and this session's comparisons are never counted twice.
- Settings are written safely when the game loop and the interface save at the same time.
- READMEs rewritten (EN/RU) with fresh screenshots.

### Install
Download `GFG-Extreme-v1_3_1.zip` below and install it with Decky Loader (*Install from zip*) over your current version; settings, profiles and what GFG learned are kept. Restart a running game so its layers update.

Frame OS Act stays experimental; A/B numbers describe your game and session.

### Verify your download
SHA-256 of the zip: `<sha256>` (see `SHA256SUMS.txt`).
