#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Opt-in GFG experimental direct real-WSI launcher.
# Do not overwrite Steam/Proton Vulkan layer paths; never mutate system files.
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
MODE=2
OP=run
ARGS=()
fail() { printf 'GSF_REAL_WSI_KIT_ERROR %s\n' "$*" >&2; exit 2; }
usage() {
cat <<'HELP'
GFG Experimental Direct Real WSI (not stable)
  bash real-wsi-game-launch.sh --check
  bash real-wsi-game-launch.sh --smoke --mode=2
  bash real-wsi-game-launch.sh --mode=2 -- /path/to/game
  bash real-wsi-game-launch.sh --mode=off -- /path/to/game

Steam game launch options:
  "/home/deck/gsf-real-wsi/real-wsi-game-launch.sh" --mode=2 -- %command%
Safe bypass without changing Steam settings:
  "/home/deck/gsf-real-wsi/real-wsi-game-launch.sh" --mode=off -- %command%
Native game/proton exit and loader diagnostics appear in ~/GFG-Real-WSI-Tests.
HELP
}
while (( $# )); do
  case "$1" in
    --check) OP=check;shift ;;
    --smoke) OP=smoke;shift ;;
    --mode=2) MODE=2;shift ;;
    --mode=3) MODE=3;shift ;;
    --mode=off) MODE=off;shift ;;
    --help|-h) usage;exit 0 ;;
    --) shift; ARGS=("$@");break ;;
    *) fail "unknown launcher option: $1" ;;
  esac
done
# Before any Vulkan/ELF prechecks, accept --mode=off as a strict passthrough.
# This makes Proton launch failures diagnosable without editing system paths.
if [[ "$MODE" == off && "$OP" != check && "$OP" != smoke ]]; then
  (( ${#ARGS[@]} > 0 )) || fail "missing game after --"
  printf 'GSF_REAL_WSI_BYPASS launcher=1 no_vulkan_override=1\n' >&2
  exec "${ARGS[@]}"
fi
[[ "$(uname -m)" == x86_64 ]] || fail "x86_64 required"
for f in libVkLayer_gfg_native.so VkLayer_gfg_native.json; do
  [[ -r "$SCRIPT_DIR/$f" ]] || fail "missing $f"
done
if [[ -r "$SCRIPT_DIR/SHA256SUMS" ]]; then
  (cd "$SCRIPT_DIR" && sha256sum --check SHA256SUMS) || fail "file integrity check failed"
fi
if command -v readelf >/dev/null 2>&1; then
  readelf -h "$SCRIPT_DIR/libVkLayer_gfg_native.so" |
    grep 'DYN (Shared object file)' >/dev/null || fail "not a shared ELF"
fi
if command -v ldd >/dev/null 2>&1; then
  if ldd "$SCRIPT_DIR/libVkLayer_gfg_native.so" | grep -q 'not found'; then
    ldd "$SCRIPT_DIR/libVkLayer_gfg_native.so" >&2
    fail "native library dependency missing; do not modify SteamOS"
  fi
fi
printf 'GSF_REAL_WSI_KIT_CHECK_OK arch=x86_64 mode=%s native_real_swapchain=1\n' "$MODE"
[[ "$OP" == check ]] && exit 0
if [[ "$OP" == smoke ]]; then
  [[ -x "$SCRIPT_DIR/wsi-gpu-smoke" ]] || fail "missing smoke program"
  ARGS=("$SCRIPT_DIR/wsi-gpu-smoke")
fi
(( ${#ARGS[@]} > 0 )) || fail "provide a game after -- or use --smoke"
# Vulkan (Wayland) games may not require DISPLAY; do not block them.
ROOT="${HOME:-/home/deck}/GFG-Real-WSI-Tests"
mkdir -p "$ROOT"
RUN="$ROOT/$(date -u +%Y%m%dT%H%M%SZ)-$$"
mkdir -p "$RUN"
printf 'mode=%s\nop=%s\nprogram=%q\ndisplay=%s\nwayland=%s\n' \
  "$MODE" "$OP" "${ARGS[0]}" "${DISPLAY:-unset}" "${WAYLAND_DISPLAY:-unset}" > "$RUN/metadata.txt"
printf 'GSF_REAL_WSI_KIT_LOG_DIR=%s\n' "$RUN" >&2
# Older Linux Vulkan Loaders (Ubuntu 22.04's in CI) ignore VK_ADD_LAYER_PATH.
# Reconstruct the normal explicit-manifest search roots rather than dropping
# them when VK_LAYER_PATH is used. Keep inherited Steam/Proton search dirs.
LAYER_DIRS=("$SCRIPT_DIR")
append_path_list() {
  local raw="$1" item
  local -a parts
  IFS=: read -r -a parts <<< "$raw"
  for item in "${parts[@]}"; do [[ -z "$item" ]] || LAYER_DIRS+=("$item"); done
}
if [[ -n "${VK_LAYER_PATH:-}" ]]; then
  append_path_list "$VK_LAYER_PATH"
else
  # Search paths are taken from the Vulkan Loader's Linux XDG conventions.
  # Steam's XDG_DATA_DIRS may include additional sandbox-managed layer dirs.
  LAYER_DIRS+=("${XDG_CONFIG_HOME:-$HOME/.config}/vulkan/explicit_layer.d"
               "${XDG_DATA_HOME:-$HOME/.local/share}/vulkan/explicit_layer.d"
               "/etc/vulkan/explicit_layer.d"
               "/usr/local/etc/vulkan/explicit_layer.d"
               "/usr/share/vulkan/explicit_layer.d"
               "/usr/local/share/vulkan/explicit_layer.d")
  append_xdg_path_list() {
    local raw="$1" item
    local -a parts
    IFS=: read -r -a parts <<< "$raw"
    for item in "${parts[@]}"; do
      [[ -z "$item" ]] || LAYER_DIRS+=("$item/vulkan/explicit_layer.d")
    done
  }
  append_xdg_path_list "${XDG_CONFIG_DIRS:-/etc/xdg}"
  append_xdg_path_list "${XDG_DATA_DIRS:-/usr/local/share:/usr/share}"
  append_path_list "${VK_ADD_LAYER_PATH:-}"
fi
export VK_LAYER_PATH="$(IFS=:; printf '%s' "${LAYER_DIRS[*]}")"
printf 'GSF_REAL_WSI_LAYER_PATH compatible_explicit=1 dirs=%s\n' "$VK_LAYER_PATH" >> "$RUN/metadata.txt"
case ":${VK_INSTANCE_LAYERS:-}:" in
  *:VK_LAYER_GFG_native:*) ;;
  *) export VK_INSTANCE_LAYERS="${VK_INSTANCE_LAYERS:+$VK_INSTANCE_LAYERS:}VK_LAYER_GFG_native" ;;
esac
export GFG_NATIVE_FG=1
export GFG_NATIVE_GPU_BRIDGE=1
export GFG_NATIVE_GPU_SYNC=same-device
export GFG_NATIVE_FORCE_FIFO=1
export GFG_NATIVE_MODE="$MODE"
export GFG_NATIVE_ASYNC=1
export GFG_NATIVE_REAL_WSI_PROBE=1
export GFG_NATIVE_TRACE=1
export GFG_NATIVE_ALGO=tiles
# Loader warnings identify bad/unknown layer manifests even if game dies
# before the first native layer log line.
export VK_LOADER_DEBUG="${VK_LOADER_DEBUG:-error,warn}"
if [[ "$OP" == smoke ]]; then
  export GFG_TEST_EXPECT_GPU=1
  export GFG_TEST_FRAMES=24
  if command -v timeout >/dev/null 2>&1; then
    ARGS=(timeout 60 "${ARGS[@]}")
  fi
fi
set +e
"${ARGS[@]}" >"$RUN/game.log" 2>&1
STATUS=$?
set -e
grep -E 'GSF_REAL_WSI_(GATE|CREATE|GPU_BRIDGE_CREATE)|\[gfg-native\].*(bypass|present|bridge)|loader.*(ERROR|WARN|error|warn)' "$RUN/game.log" >"$RUN/output-evidence.txt" || true
if ! grep -q 'GSF_REAL_WSI_GATE\|GSF_REAL_WSI_GPU_BRIDGE_CREATE' "$RUN/game.log"; then
  printf 'GSF_REAL_WSI_NO_BRIDGE_EVIDENCE launch_exit=%d (inspect game.log; driver or Vulkan layer might not have loaded)\n' "$STATUS" >&2
fi
printf 'GSF_REAL_WSI_KIT_FINISHED exit=%s logs=%s\n' "$STATUS" "$RUN" >&2
exit "$STATUS"
