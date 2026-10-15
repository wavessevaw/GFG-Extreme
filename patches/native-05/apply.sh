#!/usr/bin/env bash
# GFG Native FG Patch 05 (WSI cached Vulkan staging readback fix).
set -euo pipefail
root="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$root"
sha256sum --check --status SHA256SUMS.txt || { echo "Patch checksum mismatch." >&2; exit 1; }
src="$root/libVkLayer_gfg_native.so"
dest="${XDG_DATA_HOME:-$HOME/.local/share}/gfg-native/libVkLayer_gfg_native.so"
backup="${dest}.before-patch-05"
if [[ ! -f "$dest" || -L "$dest" ]]; then
  echo "No regular GFG Native layer at $dest. Installation refused." >&2; exit 1
fi
if cmp -s "$src" "$dest"; then echo "Patch 05 already installed."; exit 0; fi
if [[ -e "$backup" || -L "$backup" ]]; then
  echo "Patch 05 backup exists. Do not overwrite it." >&2; exit 1
fi
if ! grep -aFq 'vkNegotiateLoaderLayerInterfaceVersion' "$dest" ||
   ! grep -aFq '[gfg-native]' "$dest"; then
  echo "Existing library is not recognized as GFG Native FG." >&2; exit 1
fi
cp -p -- "$dest" "$backup"
sha256sum "$backup" > "${backup}.sha256"
tmp="${dest}.new.$$"
trap 'rm -f -- "$tmp"' EXIT
install -m 0755 "$src" "$tmp"
mv -f -- "$tmp" "$dest"
echo "GFG Native Patch 05 installed. Backup: $backup"
echo "The existing Steam launch option is unchanged."
