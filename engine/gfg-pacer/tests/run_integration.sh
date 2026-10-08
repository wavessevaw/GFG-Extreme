#!/bin/sh
# Integration test: tests/test_layer through the real Vulkan loader + mock ICD, with
# VK_LAYER_GFG_pacer found as an implicit layer in the build dir.
#   usage: MOCK_ICD_JSON=/path/VkICD_mock_icd.json tests/run_integration.sh <build-dir>
set -u
BUILD=$(cd "${1:-build}" && pwd)
: "${MOCK_ICD_JSON:?set MOCK_ICD_JSON to the mock ICD manifest}"
SHM_BASE=/dev/shm/gfg-frame-os-itest-$$
LOG=$(mktemp)
trap 'rm -f "$LOG" "$SHM_BASE"-*' EXIT
FAILED=0

# Only our layer, only the mock driver; nothing inherited from the host.
unset VK_LAYER_PATH VK_INSTANCE_LAYERS VK_LOADER_LAYERS_ENABLE VK_LOADER_LAYERS_DISABLE VK_ADD_IMPLICIT_LAYER_PATH \
      GFG_FRAME_OS GFG_FRAME_OS_ENABLE GFG_FRAME_OS_REAL_HZ GFG_FRAME_OS_SHM DISABLE_GFG_FRAME_OS
export VK_IMPLICIT_LAYER_PATH="$BUILD" VK_DRIVER_FILES="$MOCK_ICD_JSON" VK_ICD_FILENAMES="$MOCK_ICD_JSON"
export GFG_FRAME_OS_DEBUG=1

# run <name> <expect-layer: yes|no> <env...> -- <test_layer args>
run() {
    name=$1 expect=$2; shift 2
    envs=""
    while [ "$1" != "--" ]; do envs="$envs $1"; shift; done
    shift
    echo "=== $name"
    # shellcheck disable=SC2086
    env $envs "$BUILD/test_layer" "$@" >"$LOG" 2>&1
    rc=$?
    cat "$LOG"
    if grep -q '^\[gfg-pacer\] device created (swapchain hooks: yes)' "$LOG"; then loaded=yes; else loaded=no; fi
    if [ "$loaded" != "$expect" ]; then echo "FAIL $name: layer loaded=$loaded, expected $expect"; FAILED=1; fi
    if [ $rc -ne 0 ]; then echo "FAIL $name: exit $rc"; FAILED=1; fi
}

run "act, enabled from env (default shm path)" yes GFG_FRAME_OS=1 GFG_FRAME_OS_ENABLE=1 GFG_FRAME_OS_REAL_HZ=60 -- env 120
shm=$(sed -n 's/^mode=env frames=[0-9]* shm=//p' "$LOG")
if [ -n "$shm" ] && [ -e "$shm" ]; then echo "FAIL: $shm left behind"; FAILED=1; else echo "PASS layer removed its $shm at exit"; fi
run "observe (phase A)" yes GFG_FRAME_OS=1 GFG_FRAME_OS_ENABLE=1 GFG_FRAME_OS_REAL_HZ=60 GFG_FRAME_OS_MODE=observe \
    GFG_FRAME_OS_SHM="$SHM_BASE-observe" -- env 120
run "shadow (phase B)" yes GFG_FRAME_OS=1 GFG_FRAME_OS_ENABLE=1 GFG_FRAME_OS_REAL_HZ=60 GFG_FRAME_OS_MODE=shadow \
    GFG_FRAME_OS_SHM="$SHM_BASE-shadow" -- env 120

run "DXVK-like: interleaved acquires on two swapchains" yes GFG_FRAME_OS=1 GFG_FRAME_OS_ENABLE=1 \
    GFG_FRAME_OS_MODE=observe GFG_FRAME_OS_SHM="$SHM_BASE-dxvk" -- dxvk 40
run "two instances: frame-generation helper (mako-engine) created first, game (DXVK) presents" yes GFG_FRAME_OS=1 \
    GFG_FRAME_OS_ENABLE=1 GFG_FRAME_OS_MODE=observe GFG_FRAME_OS_SHM="$SHM_BASE-helper1" -- helper_first 40
run "two instances: game (DXVK) first, helper (mako-engine) created while presenting" yes GFG_FRAME_OS=1 \
    GFG_FRAME_OS_ENABLE=1 GFG_FRAME_OS_MODE=observe GFG_FRAME_OS_SHM="$SHM_BASE-helper2" -- helper_last 40
run "governor policy file (generation ack, swapchain recreation, heartbeat)" yes GFG_FRAME_OS=1 GFG_FRAME_OS_SHM="$SHM_BASE-file" -- file 120
run "loaded, not enabled" yes GFG_FRAME_OS=1 GFG_FRAME_OS_SHM="$SHM_BASE-off" -- off 120
run "version-1/2 policy files are foreign" yes GFG_FRAME_OS=1 GFG_FRAME_OS_SHM="$SHM_BASE-ver" -- badver 120
run "implicit layer not enabled (no GFG_FRAME_OS)" no GFG_FRAME_OS_ENABLE=1 GFG_FRAME_OS_REAL_HZ=60 \
    GFG_FRAME_OS_SHM="$SHM_BASE-noenv" -- off 120
run "disable_environment wins" no GFG_FRAME_OS=1 DISABLE_GFG_FRAME_OS=1 GFG_FRAME_OS_ENABLE=1 GFG_FRAME_OS_REAL_HZ=60 \
    GFG_FRAME_OS_SHM="$SHM_BASE-dis" -- off 120

if [ $FAILED -ne 0 ]; then echo "integration: FAILED"; exit 1; fi
echo "integration: all cases passed"
