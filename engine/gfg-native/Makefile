CC ?= gcc
.DEFAULT_GOAL := layer
CFLAGS ?= -std=c11 -O2 -Wall -Wextra -Werror -fPIC
BUILD ?= build
VULKAN_HEADERS ?= /usr/include
ENABLE_TE ?= 0
ENABLE_CPU_BRIDGE ?= 0
TE_LIB ?= ../gfg-temporal/build/libgfg-temporal.a
ifeq ($(ENABLE_TE),1)
NATIVE_SOURCES := src/layer.c src/gpu_bridge.c src/output_worker.c
NATIVE_HEADERS := src/cpu_bridge.h src/gpu_bridge.h src/output_worker.h src/frame_clock.h src/wsi_queries.inc src/present_ids.h src/present_chain.h src/memory_policy.h src/swapchain_chain.h ../gfg-temporal/src/te_engine.h
NATIVE_CPPFLAGS := -DGFG_NATIVE_WITH_TE -I../gfg-temporal/src
ifeq ($(ENABLE_CPU_BRIDGE),1)
NATIVE_SOURCES += src/cpu_bridge.c
NATIVE_CPPFLAGS += -DGFG_NATIVE_WITH_CPU_BRIDGE
endif
NATIVE_LDLIBS := $(TE_LIB) -ldl -lm
NATIVE_DEPS := $(TE_LIB)
else
NATIVE_SOURCES := src/layer.c
NATIVE_HEADERS := src/swapchain_chain.h
NATIVE_CPPFLAGS :=
NATIVE_LDLIBS :=
NATIVE_DEPS :=
endif

.PHONY: layer abi smoke wsi-smoke wsi-smoke-te wsi-smoke-gpu swapchain-policy memory-policy present-ids present-chain gpu-ring output-worker clean
$(BUILD)/frame-clock: tests/frame_clock.c src/frame_clock.h
	mkdir -p $(BUILD)
	$(CC) $(CFLAGS) -o $@ tests/frame_clock.c

frame-clock: $(BUILD)/frame-clock
	$(BUILD)/frame-clock
.PHONY: frame-clock
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

$(BUILD)/gpu-wsi-observer: tests/wsi_gpu_observer.c tests/gpu_observer.h src/gpu_bridge.c src/gpu_bridge.h src/present_chain.h $(TE_LIB)
	mkdir -p $(BUILD)
	$(CC) $(CFLAGS) -DVK_USE_PLATFORM_XCB_KHR -DGFG_NATIVE_TEST_SMALL -DGFG_NATIVE_TEST_GPU_OBSERVER -I$(VULKAN_HEADERS) -Isrc -I../gfg-temporal/src -o $@ tests/wsi_gpu_observer.c src/gpu_bridge.c $(TE_LIB) -lvulkan -lxcb -ldl -lpthread -lm

$(BUILD)/borrowed-device: tests/borrowed_device.c $(TE_LIB)
	mkdir -p $(BUILD)
	$(CC) $(CFLAGS) -I$(VULKAN_HEADERS) -I../gfg-temporal/src -o $@ $< $(TE_LIB) -lvulkan -ldl -lpthread -lm

$(BUILD)/present-ids: tests/present_ids.c src/present_ids.h
	mkdir -p $(BUILD)
	$(CC) $(CFLAGS) -o $@ tests/present_ids.c

present-ids: $(BUILD)/present-ids
	$(BUILD)/present-ids

$(BUILD)/present-chain: tests/present_chain.c src/present_chain.h
	mkdir -p $(BUILD)
	$(CC) $(CFLAGS) -I$(VULKAN_HEADERS) -o $@ tests/present_chain.c

present-chain: $(BUILD)/present-chain
	$(BUILD)/present-chain

$(BUILD)/gpu-ring: tests/gpu_ring.c src/gpu_bridge.c src/gpu_bridge.h src/present_chain.h $(TE_LIB)
	mkdir -p $(BUILD)
	$(CC) $(CFLAGS) -I$(VULKAN_HEADERS) -I../gfg-temporal/src -o $@ tests/gpu_ring.c $(TE_LIB) -ldl -lpthread -lm

gpu-ring: $(BUILD)/gpu-ring
	$(BUILD)/gpu-ring

$(BUILD)/output-worker: tests/output_worker.c src/output_worker.c src/output_worker.h src/present_chain.h src/gpu_bridge.h
	mkdir -p $(BUILD)
	$(CC) $(CFLAGS) -I$(VULKAN_HEADERS) -o $@ tests/output_worker.c -lpthread

output-worker: $(BUILD)/output-worker
	$(BUILD)/output-worker

$(BUILD)/queue-serialization: tests/queue_serialization.c src/layer.c
	mkdir -p $(BUILD)
	$(CC) $(CFLAGS) -Wno-unused-function -I$(VULKAN_HEADERS) -o $@ tests/queue_serialization.c -lpthread

queue-serialization: $(BUILD)/queue-serialization
	$(BUILD)/queue-serialization

# Test-only layer: inspects actual async output pixels before lower WSI.
# Keep it in its own layer directory; it must never enter the shipped package.
$(BUILD)/observer-layer/libVkLayer_gfg_native.so: $(NATIVE_SOURCES) $(NATIVE_HEADERS) tests/gpu_observer.h $(TE_LIB)
	mkdir -p $(BUILD)/observer-layer
	$(CC) $(CFLAGS) -fvisibility=hidden -I$(VULKAN_HEADERS) -Isrc -DGFG_NATIVE_WITH_TE -DGFG_NATIVE_TEST_OBSERVE_LAYER -I../gfg-temporal/src -shared -Wl,-z,defs -o $@ $(NATIVE_SOURCES) $(TE_LIB) -lvulkan -ldl -lm -lpthread
	cp VkLayer_gfg_native.json $(BUILD)/observer-layer/

$(BUILD)/async-observer-app: tests/wsi_gpu_observer.c
	mkdir -p $(BUILD)
	$(CC) $(CFLAGS) -DGFG_NATIVE_TEST_SMALL -DGFG_NATIVE_TEST_ASYNC -DVK_USE_PLATFORM_XCB_KHR -I$(VULKAN_HEADERS) -o $@ $< -lvulkan -lxcb

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

wsi-smoke-te:
	$(MAKE) ENABLE_TE=1 ENABLE_CPU_BRIDGE=1 BUILD=build-cpu layer
	$(MAKE) ENABLE_TE=1 ENABLE_CPU_BRIDGE=1 BUILD=build-cpu WSI_EXTRA_CFLAGS=-DGFG_NATIVE_TEST_SMALL build-cpu/wsi-smoke
	GFG_NATIVE_FG=1 GFG_NATIVE_CPU_BRIDGE=1 GFG_NATIVE_BUDGET_MS=5000 GFG_NATIVE_MAX_FRAME_MS=10000 GFG_NATIVE_ALGO=tiles GFG_NATIVE_LMC_TIER=2 GFG_LMC_ORPHAN_CAP=0 GFG_NATIVE_TRACE=1 \
	VK_INSTANCE_LAYERS=VK_LAYER_GFG_native VK_LAYER_PATH="$(abspath build-cpu)" \
	build-cpu/wsi-smoke

$(BUILD)/wsi-gpu-smoke: tests/wsi_gpu_smoke.c
	@test -f $(VULKAN_HEADERS)/vulkan/vulkan_xcb.h || { echo "Vulkan XCB headers required"; exit 1; }
	mkdir -p $(BUILD)
	$(CC) -std=c11 -O2 -Wall -Wextra -Werror -DVK_USE_PLATFORM_XCB_KHR -I$(VULKAN_HEADERS) -o $@ $< -lvulkan -lxcb -ldl

# GPU-resident bridge on a real XCB swapchain (lavapipe under Xvfb in CI).
# Run 1: validation layer below ours (+ sync validation) and the test-only
#        GFG_NATIVE_GPU_BRIDGE_VERIFY distinctness readback.
# Run 1b: test-only fault injection of both skip paths (TE busy, ring busy)
#        under validation: binary-semaphore invariants on every skip path.
# Run 2: no validation/verify, layer CPU-time measurement (GFG_NATIVE_TIMING).
# The skipped run-1 validation is reported, never silently passed.
GPU_SMOKE_FRAMES ?= 24
VALIDATION_LAYER_DIR ?= /usr/share/vulkan/explicit_layer.d
GPU_SMOKE_ENV := GFG_NATIVE_FG=1 GFG_NATIVE_GPU_BRIDGE=1 GFG_NATIVE_TRACE=1 GFG_NATIVE_ALGO=tiles \
	GFG_TEST_EXPECT_GPU=1 GFG_TEST_FRAMES=$(GPU_SMOKE_FRAMES)
wsi-smoke-gpu:
	$(MAKE) ENABLE_TE=1 BUILD=build-te layer
	$(MAKE) ENABLE_TE=1 BUILD=build-te build-te/wsi-gpu-smoke
	@if [ -f "$(VALIDATION_LAYER_DIR)/VkLayer_khronos_validation.json" ]; then \
	  echo "wsi-smoke-gpu: run 1 with VK_LAYER_KHRONOS_validation"; \
	  $(GPU_SMOKE_ENV) GFG_NATIVE_GPU_BRIDGE_VERIFY=1 GFG_NATIVE_GPU_BRIDGE_VERIFY_EVERY=4 \
	  GFG_TEST_VALIDATION=1 GFG_TEST_CHAIN_VK12=1 GFG_TEST_READONLY_FEATURES=1 \
	  VK_INSTANCE_LAYERS=VK_LAYER_GFG_native:VK_LAYER_KHRONOS_validation \
	  VK_LAYER_PATH="$(abspath build-te):$(VALIDATION_LAYER_DIR)" build-te/wsi-gpu-smoke && \
	  echo "wsi-smoke-gpu: run 1b skip-path fault injection with VK_LAYER_KHRONOS_validation" && \
	  $(GPU_SMOKE_ENV) GFG_NATIVE_GPU_BRIDGE_VERIFY=1 GFG_NATIVE_GPU_BRIDGE_VERIFY_EVERY=3 \
	  GFG_NATIVE_GPU_BRIDGE_INJECT_SKIP=5 GFG_TEST_ALLOW_SKIPS=1 GFG_TEST_FRAMES=30 GFG_TEST_VALIDATION=1 \
	  VK_INSTANCE_LAYERS=VK_LAYER_GFG_native:VK_LAYER_KHRONOS_validation \
	  VK_LAYER_PATH="$(abspath build-te):$(VALIDATION_LAYER_DIR)" build-te/wsi-gpu-smoke; \
	else \
	  echo "wsi-smoke-gpu: SKIP validation (VK_LAYER_KHRONOS_validation not installed)"; \
	  $(GPU_SMOKE_ENV) GFG_NATIVE_GPU_BRIDGE_VERIFY=1 GFG_NATIVE_GPU_BRIDGE_VERIFY_EVERY=4 \
	  GFG_TEST_CHAIN_VK12=1 GFG_TEST_READONLY_FEATURES=1 \
	  VK_INSTANCE_LAYERS=VK_LAYER_GFG_native VK_LAYER_PATH="$(abspath build-te)" build-te/wsi-gpu-smoke; \
	fi
	$(GPU_SMOKE_ENV) GFG_NATIVE_TIMING=1 \
	VK_INSTANCE_LAYERS=VK_LAYER_GFG_native VK_LAYER_PATH="$(abspath build-te)" build-te/wsi-gpu-smoke

GLIBC_MAX ?= 2.31
abi: $(BUILD)/libVkLayer_gfg_native.so
	@need=$$(objdump -T $< | grep -o 'GLIBC_[0-9.]*' | sed 's/GLIBC_//' | sort -V | tail -1); \
	echo "GFG native layer requires glibc $$need (limit $(GLIBC_MAX))"; \
	[ "$$(printf '%s\n%s\n' "$$need" "$(GLIBC_MAX)" | sort -V | tail -1)" = "$(GLIBC_MAX)" ]

clean:
	rm -rf $(BUILD)

$(BUILD)/hdr-precision: tests/hdr_precision.c $(TE_LIB)
	mkdir -p $(BUILD)
	$(CC) $(CFLAGS) -I$(VULKAN_HEADERS) -I../gfg-temporal/src -o $@ $< $(TE_LIB) -lvulkan -ldl -lpthread -lm
