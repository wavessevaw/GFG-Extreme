# GFG Extreme 2.1.2-shell.6 — GFG Shell beta (pre-release)

**Experimental build for hardware trials. Not verified on a Steam Deck.** Everything else is GFG Extreme 2.1.1.

**Fixed in shell.6 (GFG Shell 0.2.3):** opening a game showed "Игра запущена" before anything was started — the shell took its own Steam launch marker (Steam runs it as a non-Steam game) for a running game. Its own ids are now ignored, and the launch screen appears only for games started from the shell.

**Fixed in shell.5 (GFG Shell 0.2.2):** after quitting a non-Steam game the shell could hang on "Запуск через Steam…". The game is now recognised by any of its ids (Steam AppId, the 32-bit shortcut id, the 64-bit game id) in Steam's launch marker or in the game's `SteamGameId`; and if the game window took the screen and the shell gets it back, the launch screen closes on its own. B also stops waiting.

**Fixed in shell.4 (GFG Shell 0.2.1):** not every installed game was listed. Tools are now recognised by name only (a guessed list of tool ids could hide real games), and a game on disk counts as installed even while Steam has its "fully installed" flag cleared for an update. **Настройки → Хранилище** shows how many games each Steam library contributed, and the diagnostics zip lists every game found.

**New in shell.3 (GFG Shell 0.2.0) — redesigned to the GFG/SteamOS concept sheets:**
- **A selects and B goes back** (Godot leaves both unbound for gamepads; now bound).
- Menus own the controller: in the power menu, the main menu and Quick settings the D-pad moves only inside them; B closes them.
- No more overlapping: tiles are not zoomed any more; the focused tile gets a red ring.
- **Недавно играли** uses the newest "last played" Steam recorded (app manifest or localconfig), so Steam games show up in the right order.
- New look: full-bleed game art, red pill tabs Главная / Библиотека / Магазин, Inter font, vector icons, glyph hint bar; main menu (Menu button) with profile, Загрузки, Настройки, GFG Extreme, Питание; Quick settings (View button) with brightness and volume sliders, Wi-Fi, Autopilot / Frame Fusion / Continuous Boost switches and Сон; game page with the GFG Autopilot card (Battery / Balanced / Quality); settings with icon sidebar; Загрузки with update progress from Steam; QWERTY / ЙЦУКЕН keyboard.
- After installing this zip, open **Settings → GFG Shell → Update GFG Shell** (the Godot runtime is not downloaded again).

**Fixed in shell.2:** "Install GFG Shell" failed with `CERTIFICATE_VERIFY_FAILED`. The plugin now uses the SteamOS certificate store (and the system `curl` as a fallback); TLS verification stays on and the Godot download is still SHA-256 checked.

New: **GFG Shell**, a controller game shell (Godot 4), installed and launched from the plugin.

- **Settings → GFG Shell → Install GFG Shell.** The plugin downloads the official Godot 4.4.1 runtime once (about 60 MB, SHA-256 checked) and installs the shell into `~/.local/share/gfg-shell`. Nothing outside your home folder changes.
- **Launch GFG Shell** adds it to Steam as a non-Steam game (once) and starts it through Steam. Games you start in GFG Shell are started by Steam, so Steam Input, the overlay, Proton, launch options and cloud saves stay Steam's. Quit GFG Shell to return to Steam.
- Screens: Home (continue playing, recent, favourites), Library with filters, game page with the GFG Autopilot modes, Search with an on-screen keyboard, GFG centre (live FPS/temperature/TDP), Quick panel (View button), Settings, power menu.
- The shell talks to GFG Extreme through a local link (GFG Bridge). It only reads status and changes the same settings as the plugin (mode, Frame Fusion, Continuous Boost); TDP stays with the Governor.

Report problems with **GFG Shell → Settings → Диагностика → Собрать диагностику** (a zip on the Desktop).

**Remove GFG Shell** on the same plugin page removes the files and the Steam shortcut. To go back entirely, install the 2.1.1 release.

SHA-256: `<sha256>` — also see **SHA256SUMS.txt**.
