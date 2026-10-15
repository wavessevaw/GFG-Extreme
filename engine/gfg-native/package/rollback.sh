#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
set -euo pipefail
target="${XDG_DATA_HOME:-$HOME/.local/share}/gfg-native"
bin="$HOME/.local/bin"
backup="$target/.rollback"
[[ -f "$backup/IDENTITY" ]] && [[ "$(cat "$backup/IDENTITY")" == gfg-native-rollback-v1 ]] || {
  echo 'No valid GFG Native rollback snapshot.' >&2; exit 1;
}
for name in libVkLayer_gfg_native.so VkLayer_gfg_native.json; do
  if [[ -f "$backup/$name" ]]; then
    cp -p "$backup/$name" "$target/$name.restore"
    mv -f "$target/$name.restore" "$target/$name"
  else
    rm -f "$target/$name"
  fi
done
if [[ -f "$backup/gfg-native" ]]; then
  cp -p "$backup/gfg-native" "$bin/gfg-native.restore"
  mv -f "$bin/gfg-native.restore" "$bin/gfg-native"
else
  # Retain a transparent launcher so an existing Steam launch option works.
  mkdir -p "$bin"
  printf '#!/usr/bin/env bash\nexec "$@"\n' > "$bin/gfg-native"
  chmod 755 "$bin/gfg-native"
fi
echo 'Previous GFG Native installation restored.'
