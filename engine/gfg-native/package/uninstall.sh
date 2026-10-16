#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
set -euo pipefail
target="${XDG_DATA_HOME:-$HOME/.local/share}/gfg-native"
rm -f -- "$target/libVkLayer_gfg_native.so" "$target/VkLayer_gfg_native.json" \
  "$target/diagnose.sh" "$target/accept_report.py"
rm -rf -- "$target/.rollback"
rmdir -- "$target" 2>/dev/null || :
if [[ -f "$HOME/.local/bin/gfg-native" ]]; then
  printf '#!/usr/bin/env bash\nexec "$@"\n' > "$HOME/.local/bin/gfg-native.passthrough"
  chmod 755 "$HOME/.local/bin/gfg-native.passthrough"
  mv -f "$HOME/.local/bin/gfg-native.passthrough" "$HOME/.local/bin/gfg-native"
fi
echo 'GFG Native FG removed; transparent launcher retained for existing Steam launch options.'
