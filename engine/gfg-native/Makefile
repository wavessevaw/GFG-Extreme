CC ?= gcc
CFLAGS ?= -std=c11 -O2 -Wall -Wextra -Werror -fPIC
BUILD ?= build
VULKAN_HEADERS ?= /usr/include

.PHONY: layer abi clean
layer: $(BUILD)/libVkLayer_gfg_native.so $(BUILD)/VkLayer_gfg_native.json

$(BUILD)/libVkLayer_gfg_native.so: src/layer.c
	@test -f $(VULKAN_HEADERS)/vulkan/vk_layer.h || { echo "Vulkan headers required at $(VULKAN_HEADERS)"; exit 1; }
	mkdir -p $(BUILD)
	$(CC) $(CFLAGS) -fvisibility=hidden -I$(VULKAN_HEADERS) -shared -Wl,-z,defs -o $@ $< -lpthread

$(BUILD)/VkLayer_gfg_native.json: VkLayer_gfg_native.json
	mkdir -p $(BUILD)
	cp $< $@

GLIBC_MAX ?= 2.31
abi: $(BUILD)/libVkLayer_gfg_native.so
	@need=$$(objdump -T $< | grep -o 'GLIBC_[0-9.]*' | sed 's/GLIBC_//' | sort -V | tail -1); \
	echo "GFG native layer requires glibc $$need (limit $(GLIBC_MAX))"; \
	[ "$$(printf '%s\n%s\n' "$$need" "$(GLIBC_MAX)" | sort -V | tail -1)" = "$(GLIBC_MAX)" ]

clean:
	rm -rf $(BUILD)
