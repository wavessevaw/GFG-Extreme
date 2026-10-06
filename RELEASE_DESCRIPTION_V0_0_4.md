## GFG Extreme Decky: Governor v0.0.4 (pre-release)

**TDP control works.** Field logs showed that the Steam Deck power caps (fastPPT/slowPPT) were never written: Decky ran the plugin as the desktop user, and only root may write them, so TDP stayed at the value set in the Quick Access Menu.

> **Pre-release.** Please record a log (Home → Record log) and send it.

### Changed
- **The plugin now asks Decky for root access** (`flags: ["root"]` in `plugin.json`). Decky shows this when installing.
- **Root is used for one thing only.** On start the plugin forks a tiny helper that keeps root and accepts a single request: write a number to a `/sys/devices/…/hwmon/hwmonN/powerN_cap` file. Any other path or an out-of-range value is refused. The plugin itself immediately switches back to your user, so the launcher, configs and logs in your home folder stay yours, exactly as before.
- The log self-test reports the helper (`TDP control … writable: root helper pid …`), and every TDP write is in the action journal with the value read back.

Everything from v0.0.3 is included: the action journal, diagnostics that are never switched off silently, readable pause reasons, the in-game overlay next to vkBasalt.

### Install
1. Download `GFG-Extreme-Governor-v0_0_4.zip` and install it through Decky Loader (install from zip). Accept the root access request.
2. Close the game, press **RUN**, start the game.

### Verify your download
SHA-256 of the zip: `<sha256>` (see `SHA256SUMS.txt`).

### Known limitations
See `docs/GFG_GOVERNOR_KNOWN_LIMITATIONS.md`. 236 automated tests, all passing, including one that starts the helper as root and checks that only the helper keeps root. Not yet run on Steam Deck hardware. Renderer and Flatpak extensions are byte-identical to v0.0.2.
