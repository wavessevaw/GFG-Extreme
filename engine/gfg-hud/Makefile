CC ?= gcc
CFLAGS ?= -std=c11 -O2 -Wall -Wextra -Werror -fPIC
BUILD := build

# Vulkan bits live outside the repo (../gfg-pacer/tests/setup_vulkan_deps.sh builds them).
VULKAN_DEPS ?= /tmp/claude-0
VULKAN_HEADERS ?= $(VULKAN_DEPS)/vkh/include
VULKAN_LOADER_DIR ?= $(VULKAN_DEPS)/vkl/build/loader
MOCK_ICD_JSON ?= $(VULKAN_DEPS)/vkt/build/icd/VkICD_mock_icd.json

LAYER_SRC := src/layer.c src/overlay.c
LAYER_HDR := src/overlay.h

.PHONY: test layer abi integration clean
test: $(BUILD)/test_overlay
	$(BUILD)/test_overlay

$(BUILD)/test_overlay: tests/test_overlay.c src/overlay.c src/overlay.h
	mkdir -p $(BUILD)
	$(CC) $(CFLAGS) -o $@ tests/test_overlay.c src/overlay.c -lpthread

layer: $(BUILD)/libVkLayer_gfg_hud.so $(BUILD)/VkLayer_gfg_hud.json

$(BUILD)/libVkLayer_gfg_hud.so: $(LAYER_SRC) $(LAYER_HDR)
	@test -f $(VULKAN_HEADERS)/vulkan/vk_layer.h || { echo "Vulkan headers not found in $(VULKAN_HEADERS) (set VULKAN_HEADERS or run ../gfg-pacer/tests/setup_vulkan_deps.sh)"; exit 1; }
	mkdir -p $(BUILD)
	$(CC) $(CFLAGS) -fvisibility=hidden -I$(VULKAN_HEADERS) -shared -Wl,-z,defs -o $@ $(LAYER_SRC) -lpthread

# Games run under the Steam Runtime (sniper: glibc 2.31) or the host's newer glibc, whichever
# is newer: the shipped library may not need any symbol newer than GLIBC_MAX.
GLIBC_MAX ?= 2.31
abi: $(BUILD)/libVkLayer_gfg_hud.so
	@need=$$(objdump -T $< | grep -o 'GLIBC_[0-9.]*' | sed 's/GLIBC_//' | sort -V | tail -1); \
	echo "gfg-hud needs glibc $$need (max $(GLIBC_MAX))"; \
	[ "$$(printf '%s\n%s\n' "$$need" "$(GLIBC_MAX)" | sort -V | tail -1)" = "$(GLIBC_MAX)" ] || \
	{ objdump -T $< | grep -E 'GLIBC_2\.(3[2-9]|[4-9][0-9])'; exit 1; }
	@! objdump -T $< | grep -q '__isoc23_' || { objdump -T $< | grep '__isoc23_'; exit 1; }

# The manifest's library_path is relative: it sits next to the .so.
$(BUILD)/VkLayer_gfg_hud.json: VkLayer_gfg_hud.json
	mkdir -p $(BUILD)
	cp $< $@

$(BUILD)/test_hud: tests/test_hud.c src/overlay.h
	@test -e $(VULKAN_LOADER_DIR)/libvulkan.so || { echo "Vulkan loader not found in $(VULKAN_LOADER_DIR) (set VULKAN_LOADER_DIR or run ../gfg-pacer/tests/setup_vulkan_deps.sh)"; exit 1; }
	mkdir -p $(BUILD)
	$(CC) $(CFLAGS) -I$(VULKAN_HEADERS) -o $@ tests/test_hud.c \
		-L$(VULKAN_LOADER_DIR) -Wl,-rpath,$(VULKAN_LOADER_DIR) -lvulkan

integration: layer $(BUILD)/test_hud
	@test -f $(MOCK_ICD_JSON) || { echo "mock ICD manifest not found: $(MOCK_ICD_JSON) (set MOCK_ICD_JSON or run ../gfg-pacer/tests/setup_vulkan_deps.sh)"; exit 1; }
	MOCK_ICD_JSON=$(MOCK_ICD_JSON) tests/run_integration.sh $(BUILD)

clean:
	rm -rf $(BUILD)
