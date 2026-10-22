# GFG Extreme 3.1.1

×3 by default, Boost 2.0, a tighter dip tolerance and a quiet plugin between games. Same engine as
3.1.0 (GSF Kedavra 1.3.0).

> Tested in CI, in 38 sandbox scenarios and 39 stress runs. **Not yet checked on a Steam Deck.**
> After updating: Update engine and reboot when the panel asks.

## ×3 by default
- No mode goes above ×3 any more: above it the picture and the latency suffer. Battery, Autopilot
  on a low battery, a fixed ×3.75 and a Custom cap below 30 FPS (90 Hz) all stop at ×3.
- **Setup → Generation → Allow above ×3** unlocks ×3.75 as in 3.1.0. While it is off, ×3.75 is
  not offered on Dash and Battery shows ×3.

## Boost 2.0 (experimental, off by default)
- The second generation of Boost, rebuilt for Kedavra: a camera turn of about a second with the
  right stick (0.3 s when sharp) lowers the multiplier to ×1.75 (sharp: ×1.5, adjustable) and gives
  it back as soon as the stick rests, at most 1.5 s per turn. A flick does nothing.
- A reader thread talks to the engine directly: no wait for the 1 s control loop, there or back.
- Watts are never raised. The boost only uses what the GPU renders at the present TDP, so it shows
  most in Quality and with a fixed ×3; in Autopilot the Governor has usually spent that room as
  saved watts.
- **Setup → Experimental → Boost 2.0.**

## Governor
- Autopilot and Battery tolerate a dip of 7 % (was 12 %) before a window counts as failed.

## After a game
- Leaving a game resets everything GFG kept for it in memory. Once the TDP and the clocks are back
  with you, the plugin only watches for the next game: no pilot, Governor or Power Split work,
  the sensors for the panel every 5 s.

## Fixes
- Dash: the status block next to the ring (multiplier, FPS, phase) was boxed and wrapped since
  3.1.0, because the first-run step tiles shared its style.
