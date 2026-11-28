#!/bin/sh
# Run inside an empty benchmark directory. Arguments are Kedavra and Gamescope roots.
set -eu
k=$(realpath "$1/kedavra")
g=$(realpath "$2/src/shaders")
src=$(dirname "$(realpath "$0")")
mkdir -p spv
c++ -O2 "-DNIS_STRENGTH=${NIS_STRENGTH:-0.90}" -I"$g" "$src/nis_config.cpp" -o configure-nis
./configure-nis > nis_sdr.glsl
for pair in 'BILINEAR reduce' 'SR me' 'EASU stats' 'RCAS select'; do
    set -- $pair
    glslangValidator -V "-I$k/shaders" "-I$g" "-DMETHOD_$1" "-DRCAS_STOPS=${RCAS_STOPS:-0.2}" "$src/scale.comp" -o "spv/kfg_$2.spv"
done
glslangValidator -V "-I$k/shaders" "-I$g" "-I$PWD" "$src/nis.comp" -o spv/kfg_warp.spv
# The common host initialises all pipelines; four unused slots share the identity kernel.
for name in post smaa_edge smaa_weight smaa_blend; do cp spv/kfg_reduce.spv "spv/kfg_$name.spv"; done
for file in spv/*.spv; do spirv-val "$file"; done
cc -std=gnu11 -O2 -I"$k/engine" "$src/replay.c" "$k/engine/kfg_vk.c" -lvulkan -lm -o replay
