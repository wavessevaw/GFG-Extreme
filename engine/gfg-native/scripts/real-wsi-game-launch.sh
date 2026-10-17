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
# Preserve Steam/Proton explicit and implicit layers. A forced
# VK_LAYER_PATH/VK_INSTANCE_LAYERS override can break Gamescope, overlay
# and 32-bit Proton processes before vkCreateSwapchainKHR is reached.
# This manifest has enable_environment GFG_NATIVE_FG, so discover it
# as an opt-in implicit layer rather than forcing an explicit layer name.
if [[ -n "${VK_IMPLICIT_LAYER_PATH:-}" ]]; then
  export VK_IMPLICIT_LAYER_PATH="$SCRIPT_DIR:$VK_IMPLICIT_LAYER_PATH"
  printf 'GSF_REAL_WSI_LAYER_PATH existing_implicit_override_extended=1\n' >> "$RUN/metadata.txt"
else
  export VK_ADD_IMPLICIT_LAYER_PATH="$SCRIPT_DIR${VK_ADD_IMPLICIT_LAYER_PATH:+:$VK_ADD_IMPLICIT_LAYER_PATH}"
  printf 'GSF_REAL_WSI_LAYER_PATH added_implicit=1\n' >> "$RUN/metadata.txt"
fi
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
