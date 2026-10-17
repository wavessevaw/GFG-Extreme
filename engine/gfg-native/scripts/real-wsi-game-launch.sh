#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Experimental GFG direct REAL WSI launcher. Runs only a child game process.
# Does NOT install, replace, restart or modify SteamOS / Gamescope / Decky.
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
MODE=2
OP=run
ARGS=()
fail() { printf 'GSF_REAL_WSI_KIT_ERROR %s\n' "$*" >&2; exit 2; }
usage() {
cat <<'HELP'
GFG direct real-swapchain GPU bridge (experimental).
  bash real-wsi-game-launch.sh --check
  bash real-wsi-game-launch.sh --mode=2 -- /path/to/vulkan-game
  bash real-wsi-game-launch.sh --mode=3 -- /path/to/vulkan-game
  bash real-wsi-game-launch.sh --smoke --mode=2

Steam launch options for a Vulkan/Proton game (script path must match):
  "/home/deck/gsf-real-wsi/real-wsi-game-launch.sh" --mode=2 -- %command%

This is NOT the virtual-swapchain Deck output test.
No system install, no sudo. Stable GFG remains untouched.
Output from Vulkan and GFG appears in ~/GFG-Real-WSI-Tests/.
HELP
}
for arg in "$@"; do
  case "$arg" in
    --check) OP=check ;;
    --smoke) OP=smoke ;;
    --mode=2) MODE=2 ;;
    --mode=3) MODE=3 ;;
    --help|-h) usage;exit 0 ;;
    --) shift; ARGS=("$@");break ;;
    *) fail "unknown option before --: $arg" ;;
  esac
  shift
done
[[ "$(uname -m)" == x86_64 ]] || fail "Steam Deck x86_64 required"
for f in libVkLayer_gfg_native.so VkLayer_gfg_native.json; do
  [[ -r "$SCRIPT_DIR/$f" ]] || fail "missing $f"
done
if [[ -r "$SCRIPT_DIR/SHA256SUMS" ]]; then
  (cd "$SCRIPT_DIR" && sha256sum --check SHA256SUMS) || fail "file integrity check failed"
fi
if command -v readelf >/dev/null 2>&1; then
  readelf -h "$SCRIPT_DIR/libVkLayer_gfg_native.so" |
    grep -q 'DYN (Shared object file)' || fail "not a shared ELF"
fi
if command -v ldd >/dev/null 2>&1; then
  if ldd "$SCRIPT_DIR/libVkLayer_gfg_native.so" | grep -q 'not found'; then
    ldd "$SCRIPT_DIR/libVkLayer_gfg_native.so" >&2
    fail "native library dependency missing; do not modify SteamOS"
  fi
fi
printf 'GSF_REAL_WSI_KIT_CHECK_OK arch=x86_64 mode=%s native_real_swapchain=1\n' "$MODE"
if [[ "$OP" == check ]]; then exit 0; fi
if [[ "$OP" == smoke ]]; then
  [[ -x "$SCRIPT_DIR/wsi-gpu-smoke" ]] || fail "missing smoke program"
  ARGS=("$SCRIPT_DIR/wsi-gpu-smoke")
fi
(("${#ARGS[@]}" > 0)) || fail "provide a game after -- or run --smoke"
[[ -n "${DISPLAY:-}" ]] || fail "DISPLAY unset; launch inside Gaming Mode or desktop"
ROOT="${HOME:-/home/deck}/GFG-Real-WSI-Tests"
mkdir -p "$ROOT"
RUN="$ROOT/$(date -u +%Y%m%dT%H%M%SZ)-$$"
mkdir -p "$RUN"
printf 'kit=direct-real-WSI\nmode=%s\nargv=%q\ndisplay=%s\n' \
  "$MODE" "${ARGS[0]}" "${DISPLAY:-none}" > "$RUN/metadata.txt"
echo "GSF_REAL_WSI_KIT_LOG_DIR=$RUN" >&2
# Inherit all other game/runtime variables and only enable the layer in
# THIS game process. Ordinary non-Vulkan applications may ignore this.
export VK_LAYER_PATH="$SCRIPT_DIR"
export VK_INSTANCE_LAYERS=VK_LAYER_GFG_native
export GFG_NATIVE_FG=1
export GFG_NATIVE_GPU_BRIDGE=1
export GFG_NATIVE_GPU_SYNC=same-device
export GFG_NATIVE_FORCE_FIFO=1
export GFG_NATIVE_MODE="$MODE"
export GFG_NATIVE_ASYNC=1
export GFG_NATIVE_REAL_WSI_PROBE=1
export GFG_NATIVE_TRACE=1
export GFG_NATIVE_ALGO=tiles
# Do NOT force panel Hz until the actual Gamescope WSI refresh is measured.
if [[ "$OP" == smoke ]]; then
  export GFG_TEST_EXPECT_GPU=1
  export GFG_TEST_FRAMES=24
  if command -v timeout >/dev/null 2>&1; then ARGS=(timeout 60 "${ARGS[@]}"); fi
fi
set +e
"${ARGS[@]}" > "$RUN/game.log" 2>&1
STATUS=$?
set -e
grep -E 'GSF_REAL_WSI_(GATE|CREATE|GPU_BRIDGE_CREATE)|\[gfg-native\].*(bypass|present|bridge)' "$RUN/game.log" > "$RUN/output-evidence.txt" || true
printf 'GSF_REAL_WSI_KIT_FINISHED exit=%s logs=%s\n' "$STATUS" "$RUN" >&2
exit "$STATUS"
