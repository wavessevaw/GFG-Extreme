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
# Preserve the immediately previous installation, including absent files.
backup="$target/.rollback"
stage="$(mktemp -d "$target/.install.XXXXXX")"
trap 'rm -rf -- "$stage"' EXIT
mkdir "$stage/previous"
for name in libVkLayer_gfg_native.so VkLayer_gfg_native.json diagnose.sh accept_report.py; do
  if [[ -e "$target/$name" ]]; then cp -p "$target/$name" "$stage/previous/$name"; fi
done
if [[ -e "$bin/gfg-native" ]]; then cp -p "$bin/gfg-native" "$stage/previous/gfg-native"; fi
printf 'gfg-native-rollback-v1\n' > "$stage/previous/IDENTITY"
install -m 0755 libVkLayer_gfg_native.so "$target/libVkLayer_gfg_native.so.tmp"
install -m 0644 VkLayer_gfg_native.json "$target/VkLayer_gfg_native.json.tmp"
install -m 0755 diagnose.sh "$target/diagnose.sh.tmp"
install -m 0644 accept_report.py "$target/accept_report.py.tmp"
install -m 0755 gfg-native.sh "$bin/gfg-native.tmp"
rm -rf -- "$backup"
mv "$stage/previous" "$backup"
trap 'bash "$root/rollback.sh" >&2 || true; exit 1' ERR
mv -f "$target/libVkLayer_gfg_native.so.tmp" "$target/libVkLayer_gfg_native.so"
mv -f "$target/VkLayer_gfg_native.json.tmp" "$target/VkLayer_gfg_native.json"
mv -f "$target/diagnose.sh.tmp" "$target/diagnose.sh"
mv -f "$target/accept_report.py.tmp" "$target/accept_report.py"
mv -f "$bin/gfg-native.tmp" "$bin/gfg-native"
printf 'Internal GFG FG3 build installed; hardware acceptance NOT COMPLETED.\nSteam launch option (records diagnostics):\n%s/.local/bin/gfg-native --diagnose %%command%%\nLogs: %s/gfg-native/diagnostics/\nRollback: bash %s/rollback.sh\n' "$HOME" "${XDG_STATE_HOME:-$HOME/.local/state}" "$root"
