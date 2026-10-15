#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
set -euo pipefail
if (( $# < 1 )); then
  printf 'Usage: gfg-native <game-command> [args...]\n' >&2
  exit 2
fi
root="${XDG_DATA_HOME:-$HOME/.local/share}/gfg-native"
if [[ ! -r "$root/VkLayer_gfg_native.json" || ! -r "$root/libVkLayer_gfg_native.so" ]]; then
  echo 'GFG Native FG not installed; run install.sh' >&2
  exit 1
fi
export VK_LAYER_PATH="$root${VK_LAYER_PATH:+:$VK_LAYER_PATH}"
case ":${VK_INSTANCE_LAYERS:-}:" in
  *:VK_LAYER_GFG_native:*) ;;
  *) export VK_INSTANCE_LAYERS="VK_LAYER_GFG_native${VK_INSTANCE_LAYERS:+:$VK_INSTANCE_LAYERS}" ;;
esac
export GFG_NATIVE_FG=1
export GFG_NATIVE_CPU_BRIDGE=1
export DISABLE_MAKO=1
export DISABLE_MAKO_SPATIAL_SCALING=1
exec "$@"
