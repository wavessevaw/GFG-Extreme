# GFG Extreme theme for CSS Loader

The GFG Extreme look for the whole Steam Deck interface: near-black backgrounds, graphite panels and one red accent on toggles, sliders, progress bars and focus.

## Install
1. Install **CSS Loader** from the Decky store.
2. Copy this folder (`GFG Extreme`) to `~/homebrew/themes/` on the Deck.
3. Open CSS Loader, press **Reload themes** and switch **GFG Extreme** on.

## Options
- **Accent**: GFG Red (default), Ember or Crimson.
- **Background**: Black (as in GFG) or Graphite (a little lighter).
- **Red focus glow**: a red edge around the focused control.

## How it works
The theme re-points the colour variables Steam's gamepad UI is built on (`--gpSystem*`, `--gpColor-*`, `--gpBackground-*`). It uses no hashed class names, so a Steam client update does not break it. Anything Steam draws with hard-coded colours keeps its own look.
