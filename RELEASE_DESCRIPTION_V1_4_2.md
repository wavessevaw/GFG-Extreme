## GFG Extreme 1.4.2: playtime that stays playable

1.4.0's Playtime target did what it was told — sometimes too well. On a heavy game a long target pushed the APU down to 6 W: 10 real frames, shown as 30. A fine number on paper, unplayable in the hand. 1.4.2 puts playability first.

### Playable first
- The playtime ceiling never pushes a game below its real-frame floor — 24 in Battery, 30 in Balanced. If the game sinks below it under the ceiling, GFG raises the ceiling a watt at a time until it is playable again.
- It **remembers what each game needs to stay playable**, so the next session starts there (and re-checks half a watt lower, in case an update made the game lighter).
- When your target would need less than that, Home says so plainly: *This game needs about 9 W to stay playable, so GFG holds that: about 2h20 is realistic.*

### Choices from your game, not a fixed scale
- Instead of 2h / 3h / 4h / 5h, Home now shows how long this charge lasts **at your current pace** and offers longer times **this game can actually reach while staying playable** — up to **Max**.
- No more picking a target the game could only meet by becoming a slideshow.

### Install
Download `GFG-Extreme-v1_4_2.zip` below and install it with Decky Loader (*Install from zip*) over your current version; settings, profiles and what GFG learned are kept.

### Verify your download
SHA-256 of the zip: `<sha256>` (see `SHA256SUMS.txt`).
