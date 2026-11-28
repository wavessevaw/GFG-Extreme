#!/usr/bin/env bash
# Build the Decky install zip from the current commit with the KEDAVRA Gamescope runtime.
# Usage: scripts/build_release.sh <version> <gamescope-runtime-dir> <out-dir> [bench-dir]
#   gamescope-runtime-dir: GSF Kedavra's bundled runtime (bin/gamescope, gamescopectl, lib/, VERSION),
#   built by the release workflow from wavessevaw/GSF_Kedavra at the pinned commit.
#   bench-dir: kfg_vktest, kfg_posttest and the SPIR-V shaders (Setup -> Benchmark).
set -euo pipefail
version="$1"; runtime="$2"; out="$3"; bench="${4:-}"
root="$(git rev-parse --show-toplevel)"
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
# Export only files used on Deck, including the recovery helper, runtime notices and UI.
git -C "$root" archive --prefix=GFG-Extreme/ HEAD -- \
  main.py plugin.json package.json dist py_modules third_party_licenses \
  LICENSE.md THIRD_PARTY_NOTICES.md ASSET_PROVENANCE.md README.md README.ru.md \
  docs/img RESOURCE_OPTIMIZER.md TEST-60HZ.md NATIVE-SR.md | tar -x -C "$work"
p="$work/GFG-Extreme"
mkdir -p "$p/bin"
git -C "$root" show HEAD:tools/kfg_pacing.py > "$p/bin/kfg_pacing.py"
test -f "$runtime/bin/gamescope" || { echo "no gamescope in $runtime" >&2; exit 1; }
cp -a "$runtime" "$p/runtime"
# Workflow artifacts drop the executable bit: set it back on the binaries and the bundled loader.
chmod 755 "$p"/runtime/bin/* "$p"/runtime/lib/ld-linux*.so* 2>/dev/null || true
if [ -n "$bench" ]; then
  test -f "$bench/kfg_vktest" || { echo "no kfg_vktest in $bench" >&2; exit 1; }
  mkdir -p "$p/bench"
  cp "$bench"/kfg_vktest "$bench"/*.spv "$p/bench/"
  if [ -f "$bench/kfg_posttest" ]; then cp "$bench/kfg_posttest" "$p/bench/"; fi
  chmod 755 "$p"/bench/kfg_*test
fi
name="GFG-Extreme-v${version//./_}.zip"
mkdir -p "$out"
(cd "$work" && zip -qr -X -y "$name" GFG-Extreme)
mv "$work/$name" "$out/"
(cd "$out" && sha256sum "$name" > SHA256SUMS.txt && cat SHA256SUMS.txt)
