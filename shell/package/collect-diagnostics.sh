#!/bin/sh
# Collects GFG Shell diagnostics without starting the shell (e.g. when it does not start).
# Writes ~/Desktop/gfg-shell-diag-<time>.tar.gz. Contains no passwords or tokens.
set -u
OUT_DIR="$HOME/Desktop"; [ -d "$OUT_DIR" ] || OUT_DIR="$HOME"
T=$(date +%Y%m%d-%H%M%S)
W=$(mktemp -d)
D="$W/gfg-shell-diag-$T"; mkdir -p "$D"
BASE="${XDG_DATA_HOME:-$HOME/.local/share}"
cp -r "$BASE/gfg-shell/logs" "$D/logs" 2>/dev/null
cat "$BASE/gfg-shell/app/VERSION" >"$D/version.txt" 2>/dev/null
{ cat /etc/os-release; echo; uname -a; cat /sys/class/dmi/id/product_name 2>/dev/null; } >"$D/system.txt" 2>&1
ps -eo pid,ppid,user,etimes,args | grep -Ei 'steam|gamescope|reaper|gfg|godot|inputplumber|mangoapp' | grep -v grep >"$D/processes.txt" 2>&1
{ for d in :0 :1; do echo "== DISPLAY $d"; DISPLAY=$d xprop -root 2>&1 | grep -E 'GAMESCOPE|STEAM'; done; } >"$D/gamescope-atoms.txt" 2>&1
ls -la "$HOME/.local/share/Steam/steamapps" "$HOME/.local/share/Steam/userdata" >"$D/steam-tree.txt" 2>&1
ls -la "$HOME/.local/state/gfg-extreme/" >"$D/bridge.txt" 2>&1
systemctl --user --no-pager list-units 'gamescope*' 'steam*' >"$D/units.txt" 2>&1
tar -czf "$OUT_DIR/gfg-shell-diag-$T.tar.gz" -C "$W" "gfg-shell-diag-$T"
rm -rf "$W"
echo "$OUT_DIR/gfg-shell-diag-$T.tar.gz"
