# GFG Shell — stage B test build (pre-release)

**Not verified on a Steam Deck.** This build exists to test the stage-B hypotheses on hardware.

A controller-first game shell (Godot 4.4). Steam stays the game client: every game starts
through `steam://rungameid`, so DRM, Steam Input, the overlay, Proton, launch options, cloud
saves and achievements remain Steam's. In this stage GFG Shell runs as a non-Steam game in
the normal Gaming Mode. Nothing in SteamOS is modified; everything installs into `~/.local/share/gfg-shell`.

Screens: Home (continue playing, recent, favourites), Library (All / Installed / Favourites /
Recent / Non-Steam), game page with the GFG Autopilot card, Search with an on-screen keyboard,
GFG Extreme centre, Quick panel, Settings (display, audio, network, downloads, power, system,
GFG Extreme, diagnostics), power menu and a launch screen.

Install in Desktop Mode: unzip, `./install.sh`, then start "GFG Shell" from Gaming Mode.
See `README.txt` in the zip and `docs/GFG_SHELL.md` for the test list (H1–H8) and how to send diagnostics.

The GFG Extreme link (live FPS/temperature/TDP, mode switch) needs a GFG Extreme plugin build
that contains the GFG Bridge; without it the shell shows "GFG Extreme не подключён" and works otherwise.

Bundles the official Godot 4.4.1 runtime (MIT; sha256-pinned). GFG Shell is GPL-3.0-or-later.
