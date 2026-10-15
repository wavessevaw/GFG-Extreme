#!/usr/bin/env bash
set -euo pipefail
dest="${XDG_DATA_HOME:-$HOME/.local/share}/gfg-native/libVkLayer_gfg_native.so"
backup="${dest}.before-patch-02"
if [[ ! -f "$backup" || -L "$backup" || ! -f "${backup}.sha256" ]]; then
    printf 'Patch 02 backup or its checksum is missing. No changes made.\n' >&2
    exit 1
fi
sha256sum --check --status "${backup}.sha256" || {
    printf 'Backup checksum mismatch. Refusing rollback.\n' >&2
    exit 1
}
temporary="${dest}.rollback.$$"
trap 'rm -f -- "$temporary"' EXIT
install -m 0755 "$backup" "$temporary"
mv -f -- "$temporary" "$dest"
rm -f -- "$backup" "${backup}.sha256"
printf 'Previous GFG Native FG layer restored successfully.\n'
