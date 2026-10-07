#!/bin/bash
# Layer-order test: VK_LAYER_GFG_pacer must sit between the app and the frame generator
# (VK_LAYER_MAKO_render), or its vkQueuePresentKHR hook would also see generated presents.
#
# A fixture stands in for MAKO: it turns each present into two.  Evidence per run:
#   - loader callstack (VK_LOADER_DEBUG=layer)      app > ... > drivers
#   - gfg-pacer telemetry (observe mode)              N presents = above MAKO, 2N = below
#   - create-instance log order                       MAKO leaves before gfg-pacer reports = above
# Every case runs with both manifest enumeration orders (filenames chosen so readdir flips).
#
#   usage: MOCK_ICD_JSON=... ORDER_LOADER_DIRS="loader-dir..." tests/run_ordering.sh <build-dir>
set -u
BUILD=$(cd "${1:-build}" && pwd)
FIX=$(cd "$(dirname "$0")/fixtures" && pwd)
: "${MOCK_ICD_JSON:?set MOCK_ICD_JSON}"
LOADERS=${ORDER_LOADER_DIRS:?set ORDER_LOADER_DIRS}
N=12
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT
FAILED=0

# Filenames whose readdir order is "GFG first" / "MAKO first" on this filesystem (hash order:
# probe instead of assuming).
GFG_FIRST="" MAKO_FIRST=""
for pair in "99_gfg 00_mako" "00_gfg 99_mako" "a_gfg b_mako" "b_gfg a_mako" "gfg mako" "x_gfg y_mako" "y_gfg x_mako" \
            "VkLayer_gfg_pacer VkLayer_MAKO_render" "1 2" "2 1" "p q" "q p"; do
    set -- $pair
    rm -rf "$WORK/probe"; mkdir "$WORK/probe"; touch "$WORK/probe/$1.json" "$WORK/probe/$2.json"
    first=$(ls -f "$WORK/probe" | grep '\.json$' | head -1)
    if [ "$first" = "$1.json" ]; then [ -n "$GFG_FIRST" ] || GFG_FIRST="$1 $2"; else [ -n "$MAKO_FIRST" ] || MAKO_FIRST="$1 $2"; fi
done
if [ -z "$GFG_FIRST" ] || [ -z "$MAKO_FIRST" ]; then
    echo "FAIL: could not find manifest names that flip readdir order here"; exit 1
fi

# layout <gfg-name> <mako-name>: one implicit dir with both layers, usable through
# VK_IMPLICIT_LAYER_PATH (loader >= 1.3.296) and XDG_DATA_HOME (older loaders).
layout() {
    X=$WORK/xdg-$1; D=$X/vulkan/implicit_layer.d; GNAME=$1
    rm -rf "$X"; mkdir -p "$D"
    cp "$BUILD/libVkLayer_gfg_pacer.so" "$BUILD/fixtures/libVkLayer_MAKO_dummy.so" "$D/"
    cp "$BUILD/VkLayer_gfg_pacer.json" "$D/$1.json"
    cp "$FIX/VkLayer_MAKO_render.json" "$D/$2.json"
    ENUM=$(ls -f "$D" | grep '\.json$' | sed 's/\.json$//' | tr '\n' ' ')
}

# check <loader> <label> <expect: above|below|readdir> <env...>
check() {
    local L=$1 label=$2 expect=$3; shift 3
    local out order frames mlog want ok=1 ev
    out=$(cd "$WORK" && env -i PATH="$PATH" HOME="$WORK/home" XDG_DATA_HOME="$X" LD_LIBRARY_PATH="$L" \
        VK_IMPLICIT_LAYER_PATH="$D" VK_DRIVER_FILES="$MOCK_ICD_JSON" VK_ICD_FILENAMES="$MOCK_ICD_JSON" \
        GFG_FRAME_OS_ENABLE=1 GFG_FRAME_OS_MODE=observe GFG_FRAME_OS_SHM="$WORK/shm" GFG_FRAME_OS_DEBUG=1 \
        MAKO_DUMMY_LOG="$WORK/mako.log" VK_LOADER_DEBUG=layer,error "$@" "$BUILD/test_layer" env $N 2>&1)
    order=$(echo "$out" | awk '/layer callstack setup to:/{on=1;next} on&&/<Drivers>/{exit}
        on&&match($0,/LAYER: +VK_LAYER_[A-Za-z0-9_]+$/){n=$NF; sub(/VK_LAYER_/,"",n); s=s (s?">":"") n} END{print s}')
    frames=$(echo "$out" | sed -n 's/^telemetry: frames=\([0-9]*\).*/\1/p')
    # instance-creation log: gfg-pacer reports after its next layer returned
    ev=$(echo "$out" | grep -E '^\[(mako-dummy|gfg-pacer)\] (enter|leave|instance)' | head -3 |
         sed 's/\[mako-dummy\] enter.*/M+/; s/\[mako-dummy\] leave.*/M-/; s/\[gfg-pacer\].*/G/' | tr '\n' ' ')
    case $expect in
        above)   want="GFG_pacer>MAKO_render"; [ "$frames" = "$N" ] && [ "$ev" = "M+ M- G " ] || ok=0 ;;
        below)   want="MAKO_render>GFG_pacer"; [ "$frames" = "$((2 * N))" ] && [ "$ev" = "M+ G M- " ] || ok=0 ;;
        readdir) if [ "${ENUM%% *}" = "$GNAME" ]; then want="GFG_pacer>MAKO_render"; else want="MAKO_render>GFG_pacer"; fi ;;
    esac
    [ "$order" = "$want" ] || ok=0
    if [ $ok = 1 ]; then printf "PASS "; else printf "FAIL "; FAILED=1; fi
    printf "%-52s app>%s>drv  gfg-pacer saw %s/%s presents  [%s]\n" "$label" "${order:-none}" "${frames:-?}" "$N" "$ev"
}

mkdir -p "$WORK/home"
for L in $LOADERS; do
    ver=$(basename "$(readlink -f "$L/libvulkan.so.1")" | sed 's/^libvulkan\.so\.//')
    for names in "$GFG_FIRST" "$MAKO_FIRST"; do
        layout $names
        echo "=== loader $ver, manifests enumerate as: $ENUM"
        # (a) both implicit: order = enumeration order, i.e. not guaranteed
        check "$L" "(a) both implicit: follows readdir" readdir GFG_FRAME_OS=1 ENABLE_MAKO=1
        # recommended: both named in VK_INSTANCE_LAYERS, GFG first, implicit gates unset
        check "$L" "(b) VK_INSTANCE_LAYERS=GFG:MAKO, gates unset" above \
            VK_INSTANCE_LAYERS=VK_LAYER_GFG_pacer:VK_LAYER_MAKO_render
        # alternative: GFG implicit, MAKO only through VK_INSTANCE_LAYERS
        check "$L" "(a2) GFG implicit + VK_INSTANCE_LAYERS=MAKO" above \
            GFG_FRAME_OS=1 VK_INSTANCE_LAYERS=VK_LAYER_MAKO_render
        # control: the test must notice the wrong order
        check "$L" "(control) VK_INSTANCE_LAYERS=MAKO:GFG" below \
            VK_INSTANCE_LAYERS=VK_LAYER_MAKO_render:VK_LAYER_GFG_pacer
    done
done
if [ $FAILED -ne 0 ]; then echo "ordering: FAILED"; exit 1; fi
echo "ordering: gfg-pacer above the frame generator in every enumeration order"
