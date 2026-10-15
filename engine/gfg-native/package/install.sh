#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
set -euo pipefail
root="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$root"
sha256sum --check --status SHA256SUMS.txt || {
  echo 'GFG Native FG: package checksum verification failed.' >&2
  exit 1
}
target="${XDG_DATA_HOME:-$HOME/.local/share}/gfg-native"
bin="$HOME/.local/bin"
mkdir -p "$target" "$bin"
install -m 0755 libVkLayer_gfg_native.so "$target/libVkLayer_gfg_native.so.tmp"
install -m 0644 VkLayer_gfg_native.json "$target/VkLayer_gfg_native.json.tmp"
install -m 0755 gfg-native.sh "$bin/gfg-native.tmp"
mv -f "$target/libVkLayer_gfg_native.so.tmp" "$target/libVkLayer_gfg_native.so"
mv -f "$target/VkLayer_gfg_native.json.tmp" "$target/VkLayer_gfg_native.json"
mv -f "$bin/gfg-native.tmp" "$bin/gfg-native"
printf 'GFG Native FG installed.\nSteam launch option:\n%s/.local/bin/gfg-native %%command%%\n' "$HOME"
