#!/bin/sh
# GFG Shell launcher. Stage B: add this script to Steam as a non-Steam game and start it
# from Gaming Mode; Steam stays the game client and Steam Input keeps the controller.
HERE=$(cd "$(dirname "$0")" && pwd)
LOG_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/gfg-shell/logs"
mkdir -p "$LOG_DIR"
# Keep the previous run's console output for diagnostics.
[ -f "$LOG_DIR/stdout.log" ] && mv -f "$LOG_DIR/stdout.log" "$LOG_DIR/stdout.prev.log"
{
  echo "gfg-shell.sh $(date -Is) uid=$(id -u) display=${DISPLAY:-} wayland=${WAYLAND_DISPLAY:-} SteamGameId=${SteamGameId:-}"
} >"$LOG_DIR/stdout.log"
exec "$HERE/bin/godot" --main-pack "$HERE/gfg-shell.pck" --fullscreen \
  --rendering-driver opengl3 "$@" >>"$LOG_DIR/stdout.log" 2>&1
