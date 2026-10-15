#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
set -euo pipefail
target="${XDG_DATA_HOME:-$HOME/.local/share}/gfg-native"
rm -f -- "$target/libVkLayer_gfg_native.so" "$target/VkLayer_gfg_native.json"
rmdir -- "$target" 2>/dev/null || :
rm -f -- "$HOME/.local/bin/gfg-native"
echo 'GFG Native FG removed. Existing GFG Extreme remains unchanged.'
