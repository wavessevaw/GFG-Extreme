# GFG Extreme 3.1.0

The plugin now knows your games, takes care of your Deck's temperature, and installs its engine
before anything else. Same engine as 3.0.9 and 3.0.10 (GSF Kedavra 1.3.0).

> Tested in CI, in 36 sandbox scenarios and 39 stress runs. **Not yet checked on a Steam Deck.**

## We care about your Steam Deck's health
SteamOS lets the APU run at 85-89 °C for hours. We don't agree with that, and we want your Deck
to last. GFG Extreme deliberately holds games back from 80 °C, in every mode:

| APU temperature | What GFG Extreme does |
|---|---|
| 80 °C | No mode climbs to a more demanding point: no extra watts for extra frames |
| 85 °C | The TDP ceiling comes down a watt at a time until the Deck cools to 80 °C (was 90 °C) |
| 97 °C | The TDP drops to the minimum at once |

Every mode also stays at or below 15 W, even when SteamOS allows 20 W.

## First run: the engine first
- After installing the plugin from Decky, the panel opens on one screen: **Install engine**, then
  **Reboot now**. Dash, Graphics, Engine and Setup open only once Gamescope KEDAVRA is installed
  and running in this boot.
- A plugin update that carries a new engine asks for **Update engine** and a reboot the same way.
- If the install fails, the panel stays locked with **Try again** and **Save report**, so nothing
  runs half installed.

## Every game is remembered
- Per game, refresh rate and display (handheld or dock): the point the game held, its class
  (light, medium, heavy) and the medians of its last 9 sessions (real fps, TDP, APU draw).
- A known game starts on its point without measuring at full power again, and tries one point
  higher after 30 s in case the last session ended in a heavy scene.
- Switching games carries nothing over: the new game gets its own measurement, Governor session
  and filters.

## Light and heavy games
- A built-in list of 129 well-known Steam games with a load class.
- **Light** (DuckTales, Terraria, Hades, Celeste, Stardew Valley…): starts at 7 W, goes to x2 at
  once without a full-power measurement, and never goes above x2 in Balanced, Quality and
  Autopilot. 4-7 W is enough for these games.
- **Heavy** (The Witcher 3, Elden Ring, Cyberpunk 2077, Death Stranding…): the session starts at
  15 W.
- The Deck's own measurement always wins: a "light" game that cannot hold x2 at full power becomes
  medium, a game that holds x2 at 7 W or less becomes light even when it is not on the list.

## Dock and Steam Deck LCD
- **Dock (TV):** an external gamepad needs low latency, so no mode goes above x3 there (x2-x2.5
  when the game holds it). Autopilot keeps no watt targets on the TV; the temperature is watched
  in every mode.
- **Steam Deck LCD:** 60 Hz, or the panel's own rate when it is unlocked (for example 75 Hz).

## Fixes
- **HDR output switch now reaches Gamescope.** In 3.0.8-3.0.10 the plugin rejected its own
  `hdr_enabled` command, so the switch did nothing and the journal got a failure every second.
  A failure is now retried every 10 s and written once.

## From the 3.0.10 reports
- Generated frame on the Deck: median 592 -> 384 µs with GSF 1.3.0 (same game, filters off).
- Power Split applied its CPU cap 53 times without a single failure.
- Stable Point locked and reused points across launches.
