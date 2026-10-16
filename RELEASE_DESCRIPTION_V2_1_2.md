# GFG Extreme 2.1.2 — stable

Bug-fix and interface update for 2.1.1.

**Governor (fixes from 2.1.1 field logs)**
- A point whose frame cadence is already met is no longer rolled back when the game refuses a render-scale change: it stays at 100 % render scale, and the refused scale is not retried for that game session.
- Fractional points (for example 27 × 2.25) now confirm on the frames actually delivered. Before, they could end in a confirmation timeout although the target was being met.
- Output within 8 % of the target counts as on target (for example 83 FPS on a 90 FPS goal), so the Governor stops chasing the last few frames with extra power or experiments.
- Multipliers above ×3 (×3.25–×3.75) are now used only when no point up to ×3 reaches the goal; more power within your limit is tried first. ×4 stays the emergency fallback.
- 60 FPS is a target only on the Steam Deck LCD and on an external display. On a 90 Hz panel the target stays 90; Autopilot's reduced goal there is 45 (half the panel, even frame times).
- "Lost reliable telemetry" no longer appears every time a setting changes, and "The requested experiment was skipped" no longer repeats while a GPU-clock or shading trial is resting in its cooldown.

**Interface**
- New Home screen: an FPS ring with the GFG wolf, real × generated frames, goal ±8 % and status; small rings for real FPS, power and battery; mode tiles; Fusion and Boost switches; a filter strip.
- New Fine-tune page for Autopilot priorities, Boost and frame options. Details now opens with the GFG effort and the last session.
- **GFG Theme (CSS Loader) is removed.** A copy installed by an earlier version stays in CSS Loader; turn it off or delete it there.

**GFG Shell 0.4 — first stable release** (optional controller front-end for Gaming Mode, installed and launched from Settings → GFG Shell; Steam stays the game client). Changes since the 2.1.2 Shell test builds:
- The library now lists owned games that are not installed (they open Steam's install dialog). Fixes cover installed games that were hidden after a move to or from the SD card, games mistaken for tools, manifests without a name and non-Steam shortcuts without an id.
- Quick settings has two tabs, switched with L1 / R1. **GFG** holds the FPS ring, mode tiles, Auto priority, GFG in this game and six feature switches; **Система** holds brightness, volume, Wi-Fi, battery, sleep and the power menu.
- Fixes: the volume control works under Steam, buttons pressed in a running game no longer act in the Shell, the ☰ and ⧉ buttons are swapped back, the focus outline is drawn cleanly, and a game's title no longer runs under the Play button.
- Installing the Shell from the plugin uses the SteamOS certificate store (fixes `CERTIFICATE_VERIFY_FAILED` seen with the test builds).

Experimental parts (Temporal Engine, Frame OS Act) keep their existing switches and defaults. Automated tests cover the backend, the interface, the Shell and the release archive. No measured performance or battery-life gain is claimed by this release; Steam Deck behaviour still needs device testing.

Install **GFG-Extreme-v2_1_2.zip** through Decky (Install from zip), then restart the game.

SHA-256: `<sha256>` — also see **SHA256SUMS.txt**.
