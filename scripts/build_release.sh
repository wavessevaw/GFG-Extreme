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
# Frame OS pacer layer (64-bit), built from this commit; staged by the Governor only when a
# profile turns Frame OS on. VULKAN_HEADERS: a Vulkan-Headers include/ directory.
pacer="$work/GFG-Extreme/engine/gfg-pacer"
make -s -C "$pacer" layer abi VULKAN_HEADERS="${VULKAN_HEADERS:?set VULKAN_HEADERS to a Vulkan-Headers include dir}"
mkdir -p "$work/GFG-Extreme/bin/gfg-frame-os"
install -m 644 "$pacer/build/libVkLayer_gfg_pacer.so" "$pacer/build/VkLayer_gfg_pacer.json" \
  "$work/GFG-Extreme/bin/gfg-frame-os/"
rm -rf "$pacer/build"
# HUD layer (64-bit): copies the plugin's pre-rendered overlay into presented frames; shipped
# next to the pacer files.
hud="$work/GFG-Extreme/engine/gfg-hud"
make -s -C "$hud" layer abi VULKAN_HEADERS="$VULKAN_HEADERS"
install -m 644 "$hud/build/libVkLayer_gfg_hud.so" "$hud/build/VkLayer_gfg_hud.json" \
  "$work/GFG-Extreme/bin/gfg-frame-os/"
rm -rf "$hud/build"
if [[ "$version" =~ ^0\. ]]; then
  name="GFG-Extreme-Governor-v${version//./_}.zip"   # 0.x Governor pre-releases
else
  name="GFG-Extreme-v${version//./_}.zip"
fi
mkdir -p "$out"
(cd "$work" && zip -qr -X "$name" GFG-Extreme)
mv "$work/$name" "$out/"
(cd "$out" && sha256sum "$name" > SHA256SUMS.txt && cat SHA256SUMS.txt)
