#!/usr/bin/env bash
# Build the Decky install zip from the current commit.
# Usage: scripts/build_release.sh <version> <payload-dir> <out-dir>
#   payload-dir holds the three makorender *.flatpak bundles (not in git).
set -euo pipefail
version="$1"; payloads="$2"; out="$3"
root="$(git rev-parse --show-toplevel)"
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
git -C "$root" archive --prefix=GFG-Extreme/ HEAD | tar -x -C "$work"
rm -rf "$work/GFG-Extreme/.github"
cp "$payloads"/org.freedesktop.Platform.VulkanLayer.makorender-*.flatpak "$work/GFG-Extreme/bin/"
chmod 644 "$work"/GFG-Extreme/bin/*.flatpak
(cd "$work/GFG-Extreme/bin" && sha256sum -c --quiet SHA256SUMS.txt)
if [[ "$version" =~ ^0\. ]]; then
  name="GFG-Extreme-Governor-v${version//./_}.zip"   # 0.x Governor pre-releases
else
  name="GFG-Extreme-v${version//./_}.zip"
fi
mkdir -p "$out"
(cd "$work" && zip -qr -X "$name" GFG-Extreme)
mv "$work/$name" "$out/"
(cd "$out" && sha256sum "$name" > SHA256SUMS.txt && cat SHA256SUMS.txt)
