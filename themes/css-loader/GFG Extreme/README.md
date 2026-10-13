# GFG Extreme theme for CSS Loader

The GFG Extreme look for the whole Steam Deck interface: near-black backgrounds, graphite panels and one red accent on toggles, sliders, progress bars and focus.

## Install
1. Install **CSS Loader** from the Decky store.
2. In GFG settings, open **GFG theme** and press **Install theme**. Alternatively, copy this folder (`GFG Extreme`) to `~/homebrew/themes/` on the Deck.
3. Open CSS Loader, press **Reload themes** and switch **GFG Extreme** on.

## Options
- **Accent**: GFG Red (default), Ember or Crimson.
- **Background**: Black (as in GFG) or Graphite (a little lighter).
- **Red focus glow**: a red frame with a soft glow around the focused control and the selected game.
- **Home: last game as a vertical card** (on by default): the most recent game becomes a large vertical card like the rest of the row. Steam only loads the wide header art for that card, so it is cropped to portrait from its centre.
- **Status icons**: Accent (default, the battery charge in the accent colour), Calm (grey icons, white battery) or Steam.

## How it works
- Colours come from the variables Steam's gamepad UI is built on (`--gpSystem*`, `--gpColor-*`, `--gpBackground-*`).
- The backgrounds Steam paints itself, the home layout and the status icons use Steam class names in the form CSS Loader translates to the running client. The selectors for backgrounds follow the maintained [Obsidian](https://github.com/EMERALD0874/Steam-Deck-Themes) theme.
- Anything a client update renames keeps Steam's own look until the theme is updated. Nothing breaks.
