# GFG Extreme 2.1.2-shell.2 — GFG Shell beta (pre-release)

**Experimental build for hardware trials. Not verified on a Steam Deck.** Everything else is GFG Extreme 2.1.1.

**Fixed in shell.2:** "Install GFG Shell" failed with `CERTIFICATE_VERIFY_FAILED`. The plugin now uses the SteamOS certificate store (and the system `curl` as a fallback); TLS verification stays on and the Godot download is still SHA-256 checked.

New: **GFG Shell**, a controller game shell (Godot 4), installed and launched from the plugin.

- **Settings → GFG Shell → Install GFG Shell.** The plugin downloads the official Godot 4.4.1 runtime once (about 60 MB, SHA-256 checked) and installs the shell into `~/.local/share/gfg-shell`. Nothing outside your home folder changes.
- **Launch GFG Shell** adds it to Steam as a non-Steam game (once) and starts it through Steam. Games you start in GFG Shell are started by Steam, so Steam Input, the overlay, Proton, launch options and cloud saves stay Steam's. Quit GFG Shell to return to Steam.
- Screens: Home (continue playing, recent, favourites), Library with filters, game page with the GFG Autopilot modes, Search with an on-screen keyboard, GFG centre (live FPS/temperature/TDP), Quick panel (View button), Settings, power menu.
- The shell talks to GFG Extreme through a local link (GFG Bridge). It only reads status and changes the same settings as the plugin (mode, Frame Fusion, Continuous Boost); TDP stays with the Governor.

Report problems with **GFG Shell → Settings → Диагностика → Собрать диагностику** (a zip on the Desktop).

**Remove GFG Shell** on the same plugin page removes the files and the Steam shortcut. To go back entirely, install the 2.1.1 release.

SHA-256: `<sha256>` — also see **SHA256SUMS.txt**.
