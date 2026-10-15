#!/usr/bin/env bash
# GFG Native FG Patch 02. Compatible with installed native.1 and Patch 01.
# No root, no Steam installation mutations, no GitHub release.
set -euo pipefail
self="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$self"
sha256sum --check --status SHA256SUMS.txt || {
    printf 'Patch checksum mismatch; installation refused.\n' >&2
    exit 1
}
lib="$self/libVkLayer_gfg_native.so"
dest="${XDG_DATA_HOME:-$HOME/.local/share}/gfg-native/libVkLayer_gfg_native.so"
backup="${dest}.before-patch-02"
if [[ ! -f "$dest" || -L "$dest" ]]; then
    printf 'GFG Native FG is not installed at %s (or path is a symlink).\n' "$dest" >&2
    exit 1
fi
if cmp -s "$lib" "$dest"; then
    printf 'Patch 02 already installed. No changes made.\n'
    exit 0
fi
if [[ -e "$backup" || -L "$backup" ]]; then
    printf 'Previous Patch 02 backup exists. Refusing to overwrite it.\n' >&2
    exit 1
fi
# Verify we replace the GFG Vulkan layer, not some unrelated shared library.
if ! grep -aFq 'vkNegotiateLoaderLayerInterfaceVersion' "$dest" ||
   ! grep -aFq '[gfg-native]' "$dest"; then
    printf 'Existing library is not recognized as GFG Native FG. Refusing.\n' >&2
    exit 1
fi
cp -p -- "$dest" "$backup"
sha256sum "$backup" > "${backup}.sha256"
temporary="${dest}.new.$$"
trap 'rm -f -- "$temporary"' EXIT
install -m 0755 "$lib" "$temporary"
mv -f -- "$temporary" "$dest"
printf 'GFG Native Patch 02 installed; original saved to %s\n' "$backup"
printf 'Keep original Steam launch settings. Check swapchain candidate and reason in the log.\n'
