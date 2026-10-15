#!/bin/sh
# Installs GFG Shell for the current user only. Touches nothing outside $HOME:
#   ~/.local/share/gfg-shell/app/          program files (this package)
#   ~/.local/share/applications/gfg-shell.desktop
# Then offers it to Steam as a non-Steam game (SteamOS "Add to Steam" helper) when available.
# Undo with uninstall.sh.
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
DEST="${XDG_DATA_HOME:-$HOME/.local/share}/gfg-shell/app"
APPS="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
if [ "$(id -u)" = "0" ]; then
  echo "Run as the deck user, not root." >&2; exit 1
fi
mkdir -p "$DEST" "$APPS"
cp -f "$HERE/gfg-shell.pck" "$HERE/gfg-shell.sh" "$HERE/uninstall.sh" "$HERE/collect-diagnostics.sh" "$HERE/VERSION" "$DEST/"
mkdir -p "$DEST/bin" "$DEST/licenses"
cp -f "$HERE/bin/godot" "$DEST/bin/godot"
cp -rf "$HERE/licenses/." "$DEST/licenses/"
chmod +x "$DEST/gfg-shell.sh" "$DEST/bin/godot" "$DEST/uninstall.sh" "$DEST/collect-diagnostics.sh"
cat >"$APPS/gfg-shell.desktop" <<DESK
[Desktop Entry]
Type=Application
Name=GFG Shell
Comment=GFG controller shell (Steam stays the game client)
Exec=$DEST/gfg-shell.sh
Icon=applications-games
Categories=Game;
Terminal=false
DESK
echo "Installed GFG Shell $(cat "$HERE/VERSION") to $DEST"
if command -v steamos-add-to-steam >/dev/null 2>&1; then
  echo "Adding to Steam (Steam must be running)..."
  steamos-add-to-steam "$APPS/gfg-shell.desktop" || echo "Could not add automatically; add $DEST/gfg-shell.sh in Steam: Games > Add a Non-Steam Game."
else
  echo "Add it in Steam: Games > Add a Non-Steam Game > Browse > $DEST/gfg-shell.sh"
fi
