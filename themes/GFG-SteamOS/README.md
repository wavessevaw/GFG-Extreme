# GFG SteamOS — CSS Loader development theme

This is an implementation candidate, not the completed eight-screen mockup.
It includes CSS for eight surface families and uses Art Hero / Clean Gameview
for cinematic layouts. Matching the design on Steam Deck remains unverified.

## Installation

1. Install CSS Loader from Decky's store. Use a version supporting manifest v9.
2. In GFG Settings → GFG theme, disable the legacy GFG appearance injector.
3. Save your current CSS Loader configuration as a profile so you can restore it.
4. Extract this archive so the manifest is at
   `~/homebrew/themes/GFG-SteamOS/theme.json` (no duplicate nested directory).
5. Refresh themes in CSS Loader. Enable GFG SteamOS and accept the dependency
   installation/settings dialog. Art Hero and Clean Gameview must be available;
   their own dependencies must also resolve. Do not combine Art Hero with another
   Home layout theme such as Switch Like Home.
6. The matching development GFG plugin switches its own Decky panel to compact
   controls when it detects this theme. Existing stable GFG keeps its normal panel.

Dependency settings were checked against Art Hero v3.2.03 and Clean Gameview v1.7
source manifests. These are reference contracts, not version locks enforced by
CSS Loader; installed versions and compatibility must be checked on the device.
Dependencies are obtained through CSS Loader, not copied into this archive.

## Restore

Disable GFG SteamOS and its layout dependencies in CSS Loader, then restore the
previous CSS Loader profile. The companion returns to its ordinary panel within
two seconds when the theme marker disappears. Disabling the legacy GFG injector
alone does not disable CSS Loader themes.

## Current limits

No new native Steam top navigation, Home Play button, four-column grid geometry,
game-page GFG insertion, or combined native quick-settings/GFG page is implemented.
The compact GFG controls currently live in the existing Decky plugin panel.
No game art, fake system values, or mockup screenshots are installed as UI.
Keyboard selectors and all Steam surface selectors need real-device verification.
Steam store, system files and performance algorithms are not modified.

Sources: https://docs.deckthemes.com/CSSLoader/Features/
https://github.com/Metagawa/Steam-Deck-Themes
https://github.com/suchmememanyskill/Steam-Deck-Themes
