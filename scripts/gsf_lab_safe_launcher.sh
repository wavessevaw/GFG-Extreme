#!/usr/bin/env bash
# Experimental GSF lab launcher. Does not activate merely because ZIP installed.
set -euo pipefail
here="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
home="${HOME:?HOME is required}"
installed="$home/.local/share/gfg-native"
launcher="$home/.local/bin/gfg-native"
mode="${1:---off}"
shift || :
if [[ "$mode" == --install ]]; then
    [[ $# -eq 0 ]] || { printf 'Usage: gfg-gsf-lab.sh --install\n' >&2; exit 2; }
    [[ "$(uname -m)" == x86_64 ]] || { printf 'GSF: host is not x86_64\n' >&2; exit 2; }
    exec bash "$here/install.sh"
fi
case "$mode" in
    --off|--x2|--x3) ;;
    *)
        printf 'Usage: gfg-gsf-lab.sh [--off|--x2|--x3|--install] [--diagnose] command [args]\n' >&2
        exit 2
        ;;
esac
diagnose=0
if [[ "${1:-}" == --diagnose ]]; then diagnose=1; shift; fi
if [[ "${1:-}" == -- ]]; then shift; fi
[[ $# -ge 1 ]] || { printf 'GSF: game command missing\n' >&2; exit 2; }

# A strict bypass for safe baseline, missing component or unsupported platform.
# It strips only GFG Native, preserving Steam and other Vulkan layers.
passthrough() {
    if [[ -x "$launcher" ]]; then
        if (( diagnose )); then exec "$launcher" --off --diagnose "$@"; fi
        exec "$launcher" --off "$@"
    fi
    local var sep value item joined
    local -a fields
    for var in VK_INSTANCE_LAYERS VK_LOADER_LAYERS_ENABLE; do
        [[ -v "$var" ]] || continue
        if [[ "$var" == VK_INSTANCE_LAYERS ]]; then sep=:; else sep=,; fi
        value="${!var}"
        joined=
        IFS="$sep" read -ra fields <<< "$value"
        for item in "${fields[@]}"; do
            [[ -n "$item" && "$item" != VK_LAYER_GFG_native ]] || continue
            joined+="${joined:+$sep}$item"
        done
        if [[ -n "$joined" ]]; then export "$var=$joined"; else unset "$var"; fi
    done
    unset GFG_NATIVE_FG GFG_NATIVE_GPU_BRIDGE GFG_NATIVE_ASYNC GFG_NATIVE_FORCE_FIFO
    export DISABLE_GFG_NATIVE_FG=1
    exec "$@"
}
if [[ "$mode" == --off ]]; then passthrough "$@"; fi
if [[ "$(uname -m)" != x86_64 ]] || \
   [[ ! -x "$launcher" ]] || \
   [[ ! -r "$installed/libVkLayer_gfg_native.so" ]] || \
   [[ ! -r "$installed/VkLayer_gfg_native.json" ]] || \
   ! cmp -s "$here/libVkLayer_gfg_native.so" "$installed/libVkLayer_gfg_native.so"; then
    printf 'GSF lab: native component not installed or incompatible. Launching original game.\n' >&2
    passthrough "$@"
fi
# Explicit x2/x3 are still experimental! This is not Deck hardware acceptance.
case "$mode" in
    --x2) export GFG_NATIVE_MODE=2 ;;
    --x3) export GFG_NATIVE_MODE=3 ;;
esac
if (( diagnose )); then exec "$launcher" --diagnose "$@"; fi
exec "$launcher" "$@"
