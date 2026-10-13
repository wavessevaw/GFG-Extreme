# HUD power colours and theme installation

The TDP ring is green whenever the Deck reports external power online, including a full battery or a paused charge. On battery, its hue moves from red at 15% or below, through yellow at 40%, to green at 65% or above. Missing charge is grey unless external power is confirmed. Its number and fill continue to indicate TDP.

ENERGY remains independent: its number is the saved percentage of the device's maximum TDP allowance, and its arc indicates battery charge with the existing 50% green threshold.

Settings → GFG theme installs the bundled CSS Loader theme to the desktop user's homebrew/themes/GFG Extreme directory, without downloads. CSS Loader itself must be installed separately; reload its themes and enable GFG Extreme after copying. Reinstallation preserves extra local files. A failed directory replacement restores the previous theme.
