CC ?= gcc
CFLAGS ?= -std=c11 -O2 -Wall -Wextra -Werror -fPIC
BUILD ?= build
VULKAN_HEADERS ?= /usr/include
ENABLE_TE ?= 0
ENABLE_CPU_BRIDGE ?= 0
TE_LIB ?= ../gfg-temporal/build/libgfg-temporal.a
ifeq ($(ENABLE_TE),1)
NATIVE_SOURCES := src/layer.c src/gpu_bridge.c
NATIVE_HEADERS := src/gpu_bridge.h
NATIVE_CPPFLAGS := -DGFG_NATIVE_WITH_TE -I../gfg-temporal/src
ifeq ($(ENABLE_CPU_BRIDGE),1)
NATIVE_SOURCES += src/cpu_bridge.c
NATIVE_HEADERS += src/cpu_bridge.h src/memory_policy.h
NATIVE_CPPFLAGS += -DGFG_NATIVE_WITH_CPU_BRIDGE
endif
NATIVE_LDLIBS := $(TE_LIB) -ldl -lm
NATIVE_DEPS := $(TE_LIB)
else
NATIVE_SOURCES := src/layer.c
NATIVE_HEADERS :=
NATIVE_CPPFLAGS :=
NATIVE_LDLIBS :=
NATIVE_DEPS :=
endif

.PHONY: layer abi smoke wsi-smoke swapchain-policy memory-policy clean
layer: $(BUILD)/libVkLayer_gfg_native.so $(BUILD)/VkLayer_gfg_native.json

$(BUILD)/libVkLayer_gfg_native.so: $(NATIVE_SOURCES) $(NATIVE_HEADERS) $(NATIVE_DEPS)
	@test -f $(VULKAN_HEADERS)/vulkan/vk_layer.h || { echo "Vulkan headers required at $(VULKAN_HEADERS)"; exit 1; }
	mkdir -p $(BUILD)
	$(CC) $(CFLAGS) -fvisibility=hidden -I$(VULKAN_HEADERS) -shared -Wl,-z,defs $(NATIVE_CPPFLAGS) -o $@ $(NATIVE_SOURCES) $(NATIVE_LDLIBS) -lpthread

$(BUILD)/VkLayer_gfg_native.json: VkLayer_gfg_native.json
	mkdir -p $(BUILD)
	cp $< $@

$(BUILD)/loader-smoke: tests/loader_smoke.c
	@test -f $(VULKAN_HEADERS)/vulkan/vulkan.h || { echo "Vulkan headers required"; exit 1; }
	mkdir -p $(BUILD)
	$(CC) -std=c11 -O2 -Wall -Wextra -Werror -I$(VULKAN_HEADERS) -o $@ $< -lvulkan

smoke: layer $(BUILD)/loader-smoke
	VK_INSTANCE_LAYERS=VK_LAYER_GFG_native GFG_NATIVE_FG=1 GFG_NATIVE_TRACE=1 \
	VK_LAYER_PATH="$(abspath $(BUILD))" $(BUILD)/loader-smoke

$(BUILD)/memory-policy: tests/memory_policy.c src/memory_policy.h
	mkdir -p $(BUILD)
	$(CC) $(CFLAGS) -I$(VULKAN_HEADERS) -o $@ tests/memory_policy.c

memory-policy: $(BUILD)/memory-policy
	$(BUILD)/memory-policy

$(BUILD)/borrowed-device: tests/borrowed_device.c $(TE_LIB)
	mkdir -p $(BUILD)
	$(CC) $(CFLAGS) -I$(VULKAN_HEADERS) -I../gfg-temporal/src -o $@ $< $(TE_LIB) -lvulkan -ldl -lpthread -lm

borrowed-device: $(BUILD)/borrowed-device
	$(BUILD)/borrowed-device

$(BUILD)/gpu-wsi-observer: tests/wsi_smoke.c tests/gpu_observer.h src/gpu_bridge.c src/gpu_bridge.h $(TE_LIB)
	mkdir -p $(BUILD)
	$(CC) $(CFLAGS) -DVK_USE_PLATFORM_XCB_KHR -DGFG_NATIVE_TEST_SMALL -DGFG_NATIVE_TEST_GPU_OBSERVER -I$(VULKAN_HEADERS) -Isrc -I../gfg-temporal/src -o $@ tests/wsi_smoke.c src/gpu_bridge.c $(TE_LIB) -lvulkan -lxcb -ldl -lpthread -lm

$(BUILD)/gpu-wsi-observer-800: tests/wsi_smoke.c tests/gpu_observer.h src/gpu_bridge.c src/gpu_bridge.h $(TE_LIB)
	mkdir -p $(BUILD)
	$(CC) $(CFLAGS) -DVK_USE_PLATFORM_XCB_KHR -DGFG_NATIVE_TEST_WIDTH=1280 -DGFG_NATIVE_TEST_HEIGHT=800 -DGFG_NATIVE_TEST_GPU_OBSERVER -I$(VULKAN_HEADERS) -Isrc -I../gfg-temporal/src -o $@ tests/wsi_smoke.c src/gpu_bridge.c $(TE_LIB) -lvulkan -lxcb -ldl -lpthread -lm

$(BUILD)/gpu-wsi-stress: tests/wsi_smoke.c
	mkdir -p $(BUILD)
	$(CC) $(CFLAGS) -DVK_USE_PLATFORM_XCB_KHR -DGFG_NATIVE_TEST_SMALL -DGFG_NATIVE_TEST_ASYNC -I$(VULKAN_HEADERS) -o $@ $< -lvulkan -lxcb

$(BUILD)/gpu-wsi-resume: tests/wsi_smoke.c
	mkdir -p $(BUILD)
	$(CC) $(CFLAGS) -DVK_USE_PLATFORM_XCB_KHR -DGFG_NATIVE_TEST_SMALL -DGFG_NATIVE_TEST_RESUME -I$(VULKAN_HEADERS) -o $@ $< -lvulkan -lxcb

$(BUILD)/gpu-wsi-recreate: tests/wsi_smoke.c
	mkdir -p $(BUILD)
	$(CC) $(CFLAGS) -DVK_USE_PLATFORM_XCB_KHR -DGFG_NATIVE_TEST_SMALL -DGFG_NATIVE_TEST_RECREATE -I$(VULKAN_HEADERS) -o $@ $< -lvulkan -lxcb

$(BUILD)/swapchain-policy: tests/swapchain_policy.c src/layer.c
	mkdir -p $(BUILD)
	$(CC) $(CFLAGS) -Wno-unused-function -I$(VULKAN_HEADERS) -o $@ tests/swapchain_policy.c -lpthread

swapchain-policy: $(BUILD)/swapchain-policy
	$(BUILD)/swapchain-policy

$(BUILD)/wsi-smoke: tests/wsi_smoke.c
	@test -f $(VULKAN_HEADERS)/vulkan/vulkan_xcb.h || { echo "Vulkan XCB headers required"; exit 1; }
	mkdir -p $(BUILD)
	$(CC) -std=c11 -O2 -Wall -Wextra -Werror -DVK_USE_PLATFORM_XCB_KHR $(WSI_EXTRA_CFLAGS) -I$(VULKAN_HEADERS) -o $@ $< -lvulkan -lxcb

wsi-smoke: layer $(BUILD)/wsi-smoke
	GFG_NATIVE_FG=1 GFG_NATIVE_TRACE=1 VK_INSTANCE_LAYERS=VK_LAYER_GFG_native \
	VK_LAYER_PATH="$(abspath $(BUILD))" $(BUILD)/wsi-smoke

wsi-smoke-te: wsi-smoke-gpu

wsi-smoke-gpu:
	$(MAKE) ENABLE_TE=1 BUILD=build-te layer
	$(MAKE) ENABLE_TE=1 BUILD=build-te WSI_EXTRA_CFLAGS=-DGFG_NATIVE_TEST_SMALL build-te/wsi-smoke
	GFG_NATIVE_FG=1 GFG_NATIVE_GPU=1 GFG_NATIVE_TRACE=1 \
	VK_INSTANCE_LAYERS=VK_LAYER_GFG_native VK_LAYER_PATH="$(abspath build-te)" \
	build-te/wsi-smoke

GLIBC_MAX ?= 2.31
abi: $(BUILD)/libVkLayer_gfg_native.so
	@need=$$(objdump -T $< | grep -o 'GLIBC_[0-9.]*' | sed 's/GLIBC_//' | sort -V | tail -1); \
	echo "GFG native layer requires glibc $$need (limit $(GLIBC_MAX))"; \
	[ "$$(printf '%s\n%s\n' "$$need" "$(GLIBC_MAX)" | sort -V | tail -1)" = "$(GLIBC_MAX)" ]

clean:
	rm -rf $(BUILD)
