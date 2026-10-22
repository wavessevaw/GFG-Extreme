# GFG Extreme 3.0.8

Autopilot fixes from a Deck report (TDP 18-20 W, x3.75, 80+ C), an HDR switch, and stress runs.

> Tested in CI, in the sandbox and in 39 stress runs. **Not yet checked on a Steam Deck.**

## Autopilot
- **Never above 15 W.** SteamOS's own TDP at game start (20 W when Steam's TDP limit is off) is no
  longer Autopilot's ceiling.
- **Base 35-40 when the game holds it, x3 at least.** A point steps down only when it needs the
  whole 15 W for a minute; x3.75 is used only when x3 needs all 15 W. x2 is climbed into only at
  10 W or less and kept up to 12 W.
- **From 80 C Autopilot does not climb** to a higher point.
- **Climbs again while the Governor is paused.** Before, a paused Governor left Autopilot stuck at
  x3.75 even when the game got light.
- **SteamOS putting its TDP back** (after sleep, at a game start) is taken over again instead of
  pausing the Governor for the rest of the game.

## HDR
- **HDR output switch in Graphics.** Off: the screen and games get SDR (Gamescope `hdr_enabled 0`,
  re-sent every 10 s). On again, or when the plugin unloads, HDR comes back. A game started in HDR
  may need a restart.

## Known: the cost of generation and filters
A Deck report showed about 1.95 ms of GPU per generated frame and 1.33 ms per output frame for
vibrance + DLS + SMAA (a quarter of a busy GPU). The next builds cut this. Until then, turning SMAA
off in Graphics saves the most.

## Stress runs
`python3 -m sandbox.stress`: 30 seeded chaos hours (sleep, dock, engine gone, charger with
SteamOS re-applying its TDP, game switches) plus targeted runs (loose charger cable, slider moves,
load square wave, hot room with an empty battery, four hours of memory growth, heavy games in
Autopilot).
