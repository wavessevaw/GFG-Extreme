# GFG Extreme 3.0.6 Independence

New Dash and Graphics panels, sharper x3.75 picture in fast turns, and the first Governor 2.0
pieces: a TDP recovery journal, the 2.1.6 p5 rule and a shadow record of experiments.

> Tested in CI and in the sandbox. **Not yet checked on a Steam Deck.**

## Panel

- **Dash: rings instead of plain numbers.** TDP, APU, Pace, Color, CPU top core, GPU, CPU clock
  and fan each get a ring, the number centred in it. The colour runs from green near the ideal
  through yellow to red when the reading is way off (TDP: 9–10 W ideal, 20 W way off).
- **Mode buttons with icons** (sparkles, battery, scales, diamond), in the plugin's red and black.
- **Graphics: Look as in 2.1.6.** Preset tiles with colour swatches and a line with what is on,
  then sharpening (strength, DLS denoise) and anti-aliasing, then every effect in a two-column
  list with a counter and Clear effects. Look and Effects are now one place.

## Picture at x3.75

- KEDAVRA engine bumped to GSF 1.2.0: at base 24 the coarsest motion search is centred on the
  camera's motion when the camera turns fast. In the software test of a fast camera pan the
  worst frame went from 14.1 to 23.1 dB and the false scene cuts from 3 to 0.

## Governor

- **TDP recovery journal.** Before every TDP write the player's own TDP is saved. If the plugin
  ever dies with the TDP lowered, the next start puts the player's TDP back; a TDP changed by
  someone else in between stays.
- **p5 rule from 2.1.6.** The TDP steps down only while the slowest seconds of a window stay
  near the cap (85 % in Autopilot and Battery, 90 % otherwise). Dips like that get no extra
  watts either.
- **GPU clock ceiling** keeps a step only with enough readings in its test window.
- **Shadow record of experiments (Governor 2.0, stage 1).** TDP steps, Power Split levels and
  GPU clock steps are logged as transactions; two at once or one running too long is logged as
  a conflict. Nothing is decided by it yet: the log shows on the Deck whether only one
  experiment ever runs at a time.

Everything from 3.0.5 is included. Coming from 3.0.1 or older: Setup → Reinstall, then reboot.
