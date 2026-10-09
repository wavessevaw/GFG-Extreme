#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
set -euo pipefail
task_root=$(cd "$(dirname "$0")/../.." && pwd)
task_build=${1:-"$task_root/.gfg-open-build"}
task_output=${2:-"$task_root/bin/gfg-open"}
mkdir -p "$task_build" "$task_output"
task_pin=edd2946bd3c4281e357bd436e0e7b80df0759576
if [ ! -f "$task_build/upstream/engine/CMakeLists.txt" ]; then
 curl -fL --retry 3 "https://api.github.com/repos/eugeniosegala/MAKO/tarball/$task_pin" -o "$task_build/upstream.tar.gz"
 mkdir -p "$task_build/upstream"
 tar xzf "$task_build/upstream.tar.gz" --strip-components=1 -C "$task_build/upstream"
fi
python3 "$task_root/engine/gfg-open/embed.py"
python3 "$task_root/engine/gfg-open/patch_upstream.py" "$task_build/upstream"
cmake -S "$task_build/upstream/engine" -B "$task_build/cmake" -G Ninja \
 -DCMAKE_BUILD_TYPE=Release -DMAKO_BUILD_CLI=OFF -DBUILD_TESTING=OFF \
 -DMAKO_VULKAN_HEADERS_INCLUDE_DIR="${VULKAN_HEADERS:-/usr/include}"
cmake --build "$task_build/cmake" --target mako-render -j 4
find "$task_build/cmake" -name libmako-render.so -exec cp '{}' "$task_output/libmako-render.so" \;
test -s "$task_output/libmako-render.so"
(cd "$task_output" && sha256sum libmako-render.so > SHA256SUMS)
printf '%s\n' "GFG Open color-flow-v1; transport $task_pin; SDR8 x86_64" > "$task_output/BUILD.txt"
