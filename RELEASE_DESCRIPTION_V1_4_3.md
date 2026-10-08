## GFG Extreme 1.4.3: proven before lowered

1.4.2 made the Playtime target put playability first, but it learned what a game needs only after the ceiling had starved it once: a few seconds of slideshow before the ceiling went back up. 1.4.3 removes that moment.

### The ceiling only goes where the game has already been
- A playtime target now starts at a level the game is known to handle: the power it held in an earlier session, or the Governor's normal start level.
- From there it follows the Governor's own search down, **one proven level at a time**. A lower power becomes the ceiling only after the game has shown it keeps its frame rate there.
- Until a lower level is proven, Home shows the target as *limited*, with the time that is realistic right now. The estimate gets longer as the game proves it can do with less.
- The playable guard from 1.4.2 stays as a safety net for scenes heavier than anything seen so far.

### Install
Download `GFG-Extreme-v1_4_3.zip` below and install it with Decky Loader (*Install from zip*) over your current version; settings, profiles and what GFG learned are kept.

### Verify your download
SHA-256 of the zip: `<sha256>` (see `SHA256SUMS.txt`).
