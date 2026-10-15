CC ?= gcc
CFLAGS ?= -std=c11 -O2 -Wall -Wextra -Werror -fPIC
BUILD ?= build
VULKAN_HEADERS ?= /usr/include

.PHONY: layer abi smoke clean
layer: $(BUILD)/libVkLayer_gfg_native.so $(BUILD)/VkLayer_gfg_native.json

$(BUILD)/libVkLayer_gfg_native.so: src/layer.c
	@test -f $(VULKAN_HEADERS)/vulkan/vk_layer.h || { echo "Vulkan headers required at $(VULKAN_HEADERS)"; exit 1; }
	mkdir -p $(BUILD)
	$(CC) $(CFLAGS) -fvisibility=hidden -I$(VULKAN_HEADERS) -shared -Wl,-z,defs -o $@ $< -lpthread

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

GLIBC_MAX ?= 2.31
abi: $(BUILD)/libVkLayer_gfg_native.so
	@need=$$(objdump -T $< | grep -o 'GLIBC_[0-9.]*' | sed 's/GLIBC_//' | sort -V | tail -1); \
	echo "GFG native layer requires glibc $$need (limit $(GLIBC_MAX))"; \
	[ "$$(printf '%s\n%s\n' "$$need" "$(GLIBC_MAX)" | sort -V | tail -1)" = "$(GLIBC_MAX)" ]

clean:
	rm -rf $(BUILD)
