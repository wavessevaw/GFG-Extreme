# GFG Extreme 3.2.2

A simpler Dash and a lighter plugin, on the same GSF Kedavra engine as 3.2.1. Press **Update
engine** when the panel asks and reboot.

## Dash
- The **Mode** tiles switch generation too: tap a mode to play with it, tap the selected mode
  again to turn frame generation off (no mode is highlighted while it is off). Tap any mode to
  turn it back on.
- The separate Frame generation card is gone; the mode picks the multiplier.

## Lighter plugin
GFG's own loop runs once a second next to the game. It now does less work each second:

| Per second, in a game | 3.2.1 → 3.2.2 |
|---|---|
| Power sensor reads (TDP caps, APU draw) | 17 → 6 |
| Battery and charger scans | 1 → 0.5 |
| Telemetry file writes | 1 → 1/30 |
| hwmon folder scans | 1 → 1/60 |
| Engine mount check while the panel is open | every 5 s → once per boot |

Every feature works as before: the plugin's 39 control scenarios (Autopilot, Governor, Power
Split, GPU clock, dock, battery, menus) give identical results.
