## GFG Extreme 1.3.0: Frame OS checks itself — and remembers every game

Until now the Frame OS rings were a model's best guess. In 1.3 Frame OS **measures what it does in your own game**, keeps the score per game, and drops whatever does not pay off there.

### In-game A/B check (Frame OS Act)
- Every so often Frame OS switches **one** of its effects off for a few seconds and compares the same moment with and without it — before, during, after (A-B-A), so heat or a heavier scene cannot fake a result.
- The moment picks the test: in calm play it checks **Response** (frame timing on vs. off, same cadence), in a fight **Frames** (boost vs. calm), in a pause **Energy** (rest vs. calm, from the measured APU draw).
- After three comparisons a ring shows the **measured** number instead of the estimate. Home says *Measured in game*, the overlay shows `A/B` while a check runs, Diagnostics lists every result with its 95 % range.
- Checks are short and rare (every 20 s while learning, every 90 s once settled), never count toward the session numbers, never add watts. One switch in Diagnostics turns them off.

### Frame OS learns per game
- What the A/B check measured carries over to the next session of the same game: the rings start measured, and the checks get rarer.
- An effect that **hurts** in a game is switched off there automatically. A boost that brings **no real frames** (the GPU cannot feed it) stops — the energy stays in the bank for when it matters.
- Every eight sessions a switched-off effect gets a fresh trial: a patch or new settings can change the game.
- Diagnostics → Frame OS shows *This game*: what helps, what is off and why. *Reset what GFG learned* clears it.

### Faster boosts
- Boosts now start on the **onset** of a camera swing — a stick rising fast — about one real frame earlier, so the first fast frames are already real.

### Also in 1.3
- The recorded log reports every A/B result (mean, range, number of comparisons) and when an effect was switched off for a game.

### Install
Download `GFG-Extreme-v1_3_0.zip` below and install it with Decky Loader (*Install from zip*) over your current version; settings and profiles are kept. Restart a running game so the launcher and layers update.

Frame OS Act stays experimental. The A/B numbers describe your game and session; Response compares frame age at present, not input-to-photon latency.

### Verify your download
SHA-256 of the zip: `<sha256>` (see `SHA256SUMS.txt`).
