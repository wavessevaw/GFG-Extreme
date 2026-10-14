#!/usr/bin/env bash
# Stage GFG Shell for the GFG Extreme plugin zip (bin/gfg-shell/): the exported .pck, the
# launcher and helper scripts, VERSION, godot.json (pinned official runtime the plugin
# downloads on install) and Godot's licence texts. No Godot binary: it is ~130 MB.
# usage: shell/tools/build_bundle.sh <godot-binary> <out-dir>
set -euo pipefail
here="$(cd "$(dirname "$0")/.." && pwd)"
godot="$1"; out="$2"
. "$here/tools/godot.env"
version="$(sed -n 's/^config\/version="\(.*\)"/\1/p' "$here/project.godot")"
mkdir -p "$out/licenses"
"$godot" --headless --path "$here" --import >/dev/null 2>&1 || true
"$godot" --headless --path "$here" --export-pack Linux "$out/gfg-shell.pck" >/dev/null 2>&1
test -s "$out/gfg-shell.pck"
cp "$here"/package/gfg-shell.sh "$here"/package/uninstall.sh "$here"/package/collect-diagnostics.sh "$out/"
chmod 755 "$out"/*.sh
cp "$here"/package/licenses/* "$out/licenses/"
cp "$here/../LICENSE.md" "$out/licenses/GFG-LICENSE.md"
echo "$version" >"$out/VERSION"
python3 - "$out/godot.json" <<PY
import json, sys
json.dump({"version": "$GODOT_VERSION", "url": "$GODOT_URL", "sha256": "$GODOT_SHA256", "bin": "$GODOT_BIN"}, open(sys.argv[1], "w"), indent=1)
PY
echo "GFG Shell $version bundle: $out"
