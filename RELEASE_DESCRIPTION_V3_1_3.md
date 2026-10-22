# GFG Extreme 3.1.3

Fixes from a Deck report (Assassin's Creed Origins in the dock, TV at 60 Hz, 1600x900).
Same engine as 3.1.0 (GSF Kedavra 1.3.0). No new settings and no UI changes.

> Tested in CI, in 39 sandbox scenarios and 39 stress runs. **Not yet checked on a Steam Deck.**

## Dock
- **The dock's TDP is used.** On the dock's power SteamOS raises the TDP to 20 W, but the Governor
  pulled it back to 15 W. The pilot then decided at those 15 W that the game "does not hold x2 at
  full power" and dropped to x2.4. In the dock the ceiling is now the TDP SteamOS gives, as agreed
  for 3.1.0 ("high TDP is fine on the TV, watch the temperature"). The 80 °C guard stays. On the
  Deck's own screen nothing changes: 15 W at most.
- Cause: the Governor cleared its dock flag when a game started, just before it took the ceiling.

## Fewer point changes
- In a game with recurring heavy scenes the point went x2 → x2.4 → x2 about every 5 minutes.
  A point that falls at full power again is now retried later each time: 2, 4, 8, then 16
  minutes. In the sandbox model of that game the point changed 5 times in 38 minutes instead of
  9, and smooth time went from 81 % to 85 %.
