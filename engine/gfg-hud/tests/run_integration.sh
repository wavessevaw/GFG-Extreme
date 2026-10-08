#!/bin/sh
# Integration test: tests/test_hud through the real Vulkan loader + mock ICD, with
# VK_LAYER_GFG_hud found as an implicit layer in the build dir.  The mock ICD executes no
# commands, so besides "every call succeeded" this checks the layer's debug log: which
# swapchains got the HUD, how many frames carried it, and that nothing fell back.
#   usage: MOCK_ICD_JSON=/path/VkICD_mock_icd.json tests/run_integration.sh <build-dir>
set -u
BUILD=$(cd "${1:-build}" && pwd)
HERE=$(cd "$(dirname "$0")" && pwd)
REPO=$(cd "$HERE/../../.." && pwd)
: "${MOCK_ICD_JSON:?set MOCK_ICD_JSON to the mock ICD manifest}"
WORK=$(mktemp -d)
LOG="$WORK/log"
trap 'rm -rf "$WORK"' EXIT
FAILED=0
N=20

# Only our layer, only the mock driver; nothing inherited from the host.
unset VK_LAYER_PATH VK_INSTANCE_LAYERS VK_LOADER_LAYERS_ENABLE VK_LOADER_LAYERS_DISABLE VK_ADD_IMPLICIT_LAYER_PATH \
      GFG_HUD DISABLE_GFG_HUD EXPECT_NO_LAYER
export VK_IMPLICIT_LAYER_PATH="$BUILD" VK_DRIVER_FILES="$MOCK_ICD_JSON" VK_ICD_FILENAMES="$MOCK_ICD_JSON"
export GFG_HUD_DEBUG=1 GFG_HUD_FILE="$WORK/hud.raw" GFG_HUD_EXTENT_FILE="$WORK/hud.extent"

fail() { echo "FAIL $name: $*"; FAILED=1; }
# Lines "released (hud frames K)": total count, and how many with K == 0.
released() { grep -c 'released (hud frames' "$LOG"; }
released_zero() { grep -c 'released (hud frames 0)' "$LOG"; }

# run <name> <expect-layer: yes|no> <env...> -- <test_hud args>
run() {
    name=$1 expect=$2; shift 2
    envs=""
    while [ "$1" != "--" ]; do envs="$envs $1"; shift; done
    shift
    echo "=== $name"
    rm -f "$GFG_HUD_EXTENT_FILE"
    # shellcheck disable=SC2086
    env $envs "$BUILD/test_hud" "$@" >"$LOG" 2>&1
    rc=$?
    cat "$LOG"
    if grep -q '^\[gfg-hud\] device created (swapchain hooks: yes, hud: yes)' "$LOG"; then loaded=yes; else loaded=no; fi
    [ "$loaded" = "$expect" ] || fail "layer loaded=$loaded, expected $expect"
    [ $rc -eq 0 ] || fail "exit $rc"
    ! grep -q 'HUD off' "$LOG" || fail "a swapchain fell back to pass-through"
    ! grep -qi 'validation\|error' "$LOG" || fail "error in log"
}

run "draw: overlay updates, recreate, two swapchains per present, all formats, cleared" yes GFG_HUD=1 -- draw $N
[ "$(grep -c 'hud yes' "$LOG")" -eq 7 ] || fail "expected 7 HUD swapchains"
grep -q 'format 97: hud no: image format' "$LOG" || fail "FP16 swapchain must be no-HUD"
[ "$(released)" -eq 7 ] && [ "$(released_zero)" -eq 0 ] || fail "every HUD swapchain must have drawn"
grep -q "released (hud frames $((2 * N)))" "$LOG" || fail "recreated swapchain: $((2 * N)) HUD frames (then cleared: none)"
grep -q "overlay gen 2: 24 row regions" "$LOG" && grep -q "overlay gen 3: 0 row regions" "$LOG" || fail "overlay update / clear not picked up"
grep -q 'row regions' "$LOG" || fail "no overlay conversion logged"

if command -v python3 >/dev/null 2>&1 && [ -f "$REPO/py_modules/gfg_plugin/hud_rings.py" ]; then
    printf '1280 800\n' >"$GFG_HUD_EXTENT_FILE"
    (cd "$REPO" && python3 -c "
import sys; sys.path.insert(0, 'py_modules')
from pathlib import Path
from gfg_plugin import hud_rings as h
ok = h.write_overlay({'fps': 90, 'real': 45, 'target': 90, 'tdp': 15, 'limit': 15}, preset='standard',
                     position='bottom-right', seq=1, path=Path(sys.argv[1]), extent_path=Path(sys.argv[2]))
sys.exit(0 if ok else 1)" "$GFG_HUD_FILE" "$GFG_HUD_EXTENT_FILE") || { echo "FAIL: plugin writer"; FAILED=1; }
    run "overlay written by the plugin (hud_rings.write_overlay)" yes GFG_HUD=1 -- external $N
    grep -q "released (hud frames $N)" "$LOG" || fail "plugin overlay: expected $N HUD frames"
else
    echo "=== SKIP plugin-written overlay (no python3 / plugin sources)"
fi

for m in missing invalid toobig; do
    run "pass-through: $m overlay" yes GFG_HUD=1 -- $m $N
    [ "$(released)" -eq 2 ] && [ "$(released_zero)" -eq 2 ] || fail "$m: no HUD frames expected"
done

run "device destroyed with a live swapchain" yes GFG_HUD=1 -- leak $N
grep -q "released (hud frames $N)" "$LOG" || fail "leaked swapchain released by vkDestroyDevice"

run "implicit layer not enabled (no GFG_HUD)" no EXPECT_NO_LAYER=1 -- missing 5
run "disable_environment wins" no GFG_HUD=1 DISABLE_GFG_HUD=1 EXPECT_NO_LAYER=1 -- missing 5

if [ $FAILED -ne 0 ]; then echo "integration: FAILED"; exit 1; fi
echo "integration: all cases passed"
