#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
set -euo pipefail
disabled=0
if [[ "${1:-}" == --off ]]; then disabled=1; shift; fi
if (( $# < 1 )); then
  printf 'Usage: gfg-native [--off] <game-command> [args...]\n' >&2
  exit 2
fi
root="${XDG_DATA_HOME:-$HOME/.local/share}/gfg-native"
if (( disabled )) || [[ "${GFG_NATIVE_MODE:-3}" == off ]] || \
   [[ ! -r "$root/VkLayer_gfg_native.json" || ! -r "$root/libVkLayer_gfg_native.so" ]]; then
  unset GFG_NATIVE_FG GFG_NATIVE_GPU GFG_NATIVE_CPU_BRIDGE
  export DISABLE_GFG_NATIVE_FG=1
  exec "$@"
fi
export VK_LAYER_PATH="$root${VK_LAYER_PATH:+:$VK_LAYER_PATH}"
case ":${VK_INSTANCE_LAYERS:-}:" in
  *:VK_LAYER_GFG_native:*) ;;
  *) export VK_INSTANCE_LAYERS="VK_LAYER_GFG_native${VK_INSTANCE_LAYERS:+:$VK_INSTANCE_LAYERS}" ;;
esac
unset DISABLE_GFG_NATIVE_FG
export GFG_NATIVE_FG=1
export GFG_NATIVE_GPU=1
unset GFG_NATIVE_CPU_BRIDGE
export DISABLE_MAKO=1
export DISABLE_MAKO_SPATIAL_SCALING=1
exec "$@"
