## GFG Extreme Decky: Governor v0.0.3 (pre-release)

This release fixes the problems found in the first v0.0.2 field logs and adds a detailed action journal, so every log shows exactly what was clicked, launched and changed.

> **Pre-release.** Please record a log (Home → Record log) and send it.

### Fixed
- **Governor stuck on "Paused / Waiting" forever.** A stale renderer diagnostics log owned by another user (or a symlink) made the launch wrapper switch diagnostics off without a trace, so the Governor never received FPS, never left PAUSED, and the effort stayed "assessing". The wrapper now removes such stale files from its own config folder and, as a last resort, writes to the RAM log the Governor also reads.
- **The pause now says why.** Instead of a bare "Waiting" the plugin shows the reason: restart the game, the game is not running, no FPS from the engine, TDP changed outside GFG, and so on.
- **No silent TDP failures.** When the power caps are not writable, the plugin says **No TDP access** instead of pretending to manage power.
- **In-game overlay next to vkBasalt shader effects** (from PR #12), plus a check that MangoHud is actually loaded in the running game.

### New: action journal
A new `activity.jsonl` records, in order, with timestamps:
- every action in the plugin UI (Run/Stop, overlay, profiles, settings, record log, copying the launch command), with its result or error;
- every game launch through the GFG launcher: profile, whether diagnostics and the Governor overlay were attached, and why not;
- the game being detected and exiting;
- every Governor state change with its reason;
- every TDP claim, write and restore with the result and the actual value read back.

The log zip (Record log) now also contains this journal, starting 30 minutes **before** the recording, plus launch manifests, running game processes and new self-tests (diagnostics marker, diagnostics log ownership, MangoHud).

### Install
1. Download `GFG-Extreme-Governor-v0_0_3.zip` and install it through Decky Loader (install from zip).
2. Open the plugin. The launcher is regenerated automatically (wrapper format 79).
3. Close the game, press **RUN**, start the game.

### Verify your download
SHA-256 of the zip: `021e423d1dcb46fe283ea2adb3258b122eb27f724b81d6b423d9f13f43b36113` (see `SHA256SUMS.txt`).

### Known limitations
- **TDP control needs root access.** Decky runs this plugin as the desktop user, and the Steam Deck power caps can only be written by root. Until the plugin gets root access, it manages frame generation only and shows **No TDP access**.
- See `docs/GFG_GOVERNOR_KNOWN_LIMITATIONS.md`. 231 automated tests, all passing. Renderer and Flatpak extensions are byte-identical to v0.0.2.
