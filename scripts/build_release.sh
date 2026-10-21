#!/usr/bin/env bash
# Build the Decky install zip from the current commit with the KEDAVRA Gamescope runtime.
# Usage: scripts/build_release.sh <version> <gamescope-runtime-dir> <out-dir>
#   gamescope-runtime-dir: GSF Kedavra's bundled runtime (bin/gamescope, gamescopectl, lib/, VERSION),
#   built by the release workflow from wavessevaw/GSF_Kedavra at the pinned commit.
set -euo pipefail
version="$1"; runtime="$2"; out="$3"
root="$(git rev-parse --show-toplevel)"
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
git -C "$root" archive --prefix=GFG-Extreme/ HEAD | tar -x -C "$work"
p="$work/GFG-Extreme"
rm -rf "$p/.github" "$p/tests" "$p/sandbox" "$p/frontend" "$p/branding" "$p/tools" "$p/node_modules"
test -x "$runtime/bin/gamescope" || { echo "no gamescope in $runtime" >&2; exit 1; }
cp -a "$runtime" "$p/runtime"
chmod 755 "$p"/runtime/bin/* 2>/dev/null || true
name="GFG-Extreme-v${version//./_}.zip"
mkdir -p "$out"
(cd "$work" && zip -qr -X -y "$name" GFG-Extreme)
mv "$work/$name" "$out/"
(cd "$out" && sha256sum "$name" > SHA256SUMS.txt && cat SHA256SUMS.txt)
