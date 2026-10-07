#!/bin/sh
# Fetch and build what `make layer integration` needs, outside the repo:
#   $VULKAN_DEPS/vkh  Vulkan-Headers   (include/ used by the layer and the test)
#   $VULKAN_DEPS/vkl  Vulkan-Loader    (build/loader/libvulkan.so)
#   $VULKAN_DEPS/vkt  Vulkan-Tools     (build/icd: mock ICD only)
# Headers and loader/tools are pinned to the same SDK tag.
set -eu
DEPS=${VULKAN_DEPS:-/tmp/claude-0}
TAG=${VULKAN_TAG:-v1.4.365}
mkdir -p "$DEPS"
fetch() { [ -d "$DEPS/$2" ] || git -c advice.detachedHead=false clone -q --depth 1 --branch "$TAG" "https://github.com/KhronosGroup/$1" "$DEPS/$2"; }
fetch Vulkan-Headers vkh
fetch Vulkan-Loader vkl
fetch Vulkan-Tools vkt
cmake -S "$DEPS/vkh" -B "$DEPS/vkh/build" -G Ninja -DCMAKE_INSTALL_PREFIX="$DEPS/vkh/build/install" >/dev/null
cmake --install "$DEPS/vkh/build" >/dev/null
cmake -S "$DEPS/vkl" -B "$DEPS/vkl/build" -G Ninja -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTS=OFF \
    -DVULKAN_HEADERS_INSTALL_DIR="$DEPS/vkh/build/install" \
    -DBUILD_WSI_XCB_SUPPORT=OFF -DBUILD_WSI_XLIB_SUPPORT=OFF -DBUILD_WSI_WAYLAND_SUPPORT=OFF >/dev/null
ninja -C "$DEPS/vkl/build" >/dev/null
cmake -S "$DEPS/vkt" -B "$DEPS/vkt/build" -G Ninja -DCMAKE_BUILD_TYPE=Release -DBUILD_CUBE=OFF -DBUILD_VULKANINFO=OFF \
    -DBUILD_ICD=ON -DCMAKE_PREFIX_PATH="$DEPS/vkh/build/install" \
    -DBUILD_WSI_XCB_SUPPORT=OFF -DBUILD_WSI_XLIB_SUPPORT=OFF -DBUILD_WSI_WAYLAND_SUPPORT=OFF >/dev/null
ninja -C "$DEPS/vkt/build" >/dev/null
echo "Vulkan deps ready in $DEPS"
