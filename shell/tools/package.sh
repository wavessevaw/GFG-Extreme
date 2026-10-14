#!/usr/bin/env bash
# Build the GFG Shell package: gfg-shell-<version>.zip with the pinned Godot runtime,
# the exported .pck, install/uninstall/diagnostics scripts and licenses.
# usage: tools/package.sh <out-dir> [godot-cache-dir]
set -euo pipefail
here="$(cd "$(dirname "$0")/.." && pwd)"
out="$(mkdir -p "$1" && cd "$1" && pwd)"
cache="${2:-${RUNNER_TEMP:-/tmp}/gfg-godot}"
. "$here/tools/godot.env"
version="$(sed -n 's/^config\/version="\(.*\)"/\1/p' "$here/project.godot")"
mkdir -p "$cache"
if [ ! -x "$cache/$GODOT_BIN" ]; then
  curl -fsSL -o "$cache/godot.zip" "$GODOT_URL"
  echo "$GODOT_SHA256  $cache/godot.zip" | sha256sum -c -
  unzip -o -q "$cache/godot.zip" -d "$cache"
  curl -fsSL -o "$cache/LICENSE.txt" "https://raw.githubusercontent.com/godotengine/godot/$GODOT_VERSION/LICENSE.txt"
  curl -fsSL -o "$cache/COPYRIGHT.txt" "https://raw.githubusercontent.com/godotengine/godot/$GODOT_VERSION/COPYRIGHT.txt"
fi
godot="$cache/$GODOT_BIN"
work="$(mktemp -d)"; trap 'rm -rf "$work"' EXIT
pkg="$work/gfg-shell-$version"
mkdir -p "$pkg/bin" "$pkg/licenses"
"$godot" --headless --path "$here" --import >/dev/null 2>&1 || true
"$godot" --headless --path "$here" --export-pack Linux "$pkg/gfg-shell.pck"
test -s "$pkg/gfg-shell.pck"
cp "$godot" "$pkg/bin/godot"
cp "$here"/package/*.sh "$pkg/"
cp "$here/package/README.txt" "$pkg/"
echo "$version" >"$pkg/VERSION"
cp "$cache/LICENSE.txt" "$pkg/licenses/GODOT-LICENSE.txt"
cp "$cache/COPYRIGHT.txt" "$pkg/licenses/GODOT-COPYRIGHT.txt"
cp "$here/../LICENSE.md" "$pkg/licenses/GFG-LICENSE.md"
chmod +x "$pkg"/*.sh "$pkg/bin/godot"
(cd "$pkg" && sha256sum gfg-shell.pck bin/godot *.sh >SHA256SUMS.txt)
(cd "$work" && zip -q -r -y "$out/gfg-shell-$version.zip" "gfg-shell-$version")
(cd "$out" && sha256sum "gfg-shell-$version.zip" >"gfg-shell-$version.zip.sha256")
echo "$out/gfg-shell-$version.zip"
