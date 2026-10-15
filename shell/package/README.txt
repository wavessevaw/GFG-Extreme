GFG Shell — stage B test build (not verified on a Steam Deck yet)

What it is: a controller-first game shell (Godot 4). Steam stays the game client:
every game starts through Steam (steam://rungameid), so DRM, Steam Input, the
overlay, Proton, launch options, cloud saves and achievements are Steam's own.
In this stage GFG Shell runs as a non-Steam game inside the normal Gaming Mode.
Nothing in SteamOS is changed; quitting GFG Shell returns you to Steam.

Install (Desktop Mode, Konsole):
  unzip gfg-shell-*.zip && cd gfg-shell-*/ && ./install.sh
  If Steam was running, GFG Shell appears in Steam as a non-Steam game.
  Otherwise: Steam > Games > Add a Non-Steam Game > Browse >
  ~/.local/share/gfg-shell/app/gfg-shell.sh
In Steam, set the GFG Shell controller layout to "Gamepad" (default for non-Steam).

Controls: D-pad/stick move · A select · B back · L1/R1 sections · View = Quick panel ·
Menu = Power · X = Search · Y = favourite (game page). Steam and "..." stay Steam's.

GFG Extreme link: shows live FPS/CPU/GPU/temperature/TDP and lets you choose
Battery/Balanced/Quality/Autopilot, Frame Fusion and Continuous Boost. It needs a
GFG Extreme plugin build that contains the GFG Bridge; without it the shell works
and shows "GFG Extreme не подключён".

Diagnostics: Settings > Диагностика > "Собрать диагностику" (zip on the Desktop),
or ./collect-diagnostics.sh if the shell does not start.
Remove: ~/.local/share/gfg-shell/app/uninstall.sh  (--all also deletes logs/settings)

Licenses: GFG Shell GPL-3.0-or-later; Godot Engine MIT (licenses/).
