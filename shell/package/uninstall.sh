#!/bin/sh
# Removes GFG Shell program files and its menu entry. Keeps logs and settings unless --all.
# The Steam shortcut (if added) is removed in Steam: right-click > Manage > Remove non-Steam game.
set -eu
BASE="${XDG_DATA_HOME:-$HOME/.local/share}"
rm -rf "$BASE/gfg-shell/app"
rm -f "$BASE/applications/gfg-shell.desktop"
if [ "${1:-}" = "--all" ]; then
  rm -rf "$BASE/gfg-shell" "$HOME/.local/share/godot/app_userdata/GFG Shell"
fi
echo "GFG Shell removed. Remove its Steam shortcut in Steam if you added one."
