#!/usr/bin/env bash
set -euo pipefail
dest="${XDG_DATA_HOME:-$HOME/.local/share}/gfg-native/libVkLayer_gfg_native.so"
backup="${dest}.before-patch-03"
if [[ ! -f "$backup" || -L "$backup" || ! -f "${backup}.sha256" ]]; then
  echo "Patch 03 backup not found." >&2; exit 1
fi
sha256sum --check --status "${backup}.sha256" || {
  echo "Backup checksum verification failed." >&2; exit 1
}
tmp="${dest}.rollback.$$"
trap 'rm -f -- "$tmp"' EXIT
install -m 0755 "$backup" "$tmp"
mv -f -- "$tmp" "$dest"
rm -f -- "$backup" "${backup}.sha256"
echo "Pre-patch-03 Vulkan layer restored."
