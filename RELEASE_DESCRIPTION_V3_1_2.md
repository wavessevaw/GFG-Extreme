# GFG Extreme 3.1.2

Optimisation: less work for the Deck's CPU while you play, and fixes for a few logic errors.
Same engine as 3.1.0 (GSF Kedavra 1.3.0). No new settings and no UI changes.

> Tested in CI, in 38 sandbox scenarios and 39 stress runs. The CPU numbers below were measured in
> the sandbox on a PC, not on a Steam Deck. **Not yet checked on a Steam Deck.**

## Less load while playing
- **HUD.** Drawing the HUD took about 90 % of GFG's per-second work. Each ring is now drawn once
  for every fill level and reused, and the panel's shape is computed once per HUD size. The
  picture is pixel for pixel the same, and drawing it takes about a third of the CPU it did.
- **Policy sends.** Each change of point started seven `gamescopectl` processes. Now only the
  values the engine does not already report are sent, plus the revision. That halves the
  `gamescopectl` starts over a session (133 → 61 in four 30-minute sandbox games). After an
  engine restart everything is sent again, as before.
- **Boost 2.0.** The stick reader woke up for every controller report (250 times a second). Now
  it wakes at most 25 times a second and reads what queued up. A turn still registers within
  40 ms, far under the 0.3 s a turn needs.
- **Panel.** While the panel is open, the device name and the check for other frame-generation
  plugins are re-read every 5 s instead of every second.

## Fixes
- **Governor.** After the engine status went stale (a hitch, a long load), the next reading
  counted every late frame from the whole stale period as one second's worth. That could look
  like a sudden overload and make the Governor raise the TDP. Now each reading covers only its
  own second.
