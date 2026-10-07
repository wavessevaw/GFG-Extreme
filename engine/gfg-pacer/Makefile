CC ?= gcc
CFLAGS ?= -std=c11 -O2 -Wall -Wextra -Werror -fPIC
BUILD := build

# Vulkan bits live outside the repo (tests/setup_vulkan_deps.sh builds them).
VULKAN_DEPS ?= /tmp/claude-0
VULKAN_HEADERS ?= $(VULKAN_DEPS)/vkh/include
VULKAN_LOADER_DIR ?= $(VULKAN_DEPS)/vkl/build/loader
MOCK_ICD_JSON ?= $(VULKAN_DEPS)/vkt/build/icd/VkICD_mock_icd.json

LAYER_SRC := src/layer.c src/control.c src/metrics.c src/scheduler.c
LAYER_HDR := src/control.h src/metrics.h src/scheduler.h

.PHONY: test layer abi integration ordering clean
test: $(BUILD)/test_scheduler $(BUILD)/test_control
	$(BUILD)/test_scheduler
	$(BUILD)/test_control

$(BUILD)/test_scheduler: tests/test_scheduler.c src/scheduler.c src/scheduler.h
	mkdir -p $(BUILD)
	$(CC) $(CFLAGS) -o $@ tests/test_scheduler.c src/scheduler.c -lm

$(BUILD)/test_control: tests/test_control.c src/control.c src/metrics.c src/scheduler.c $(LAYER_HDR)
	mkdir -p $(BUILD)
	$(CC) $(CFLAGS) -o $@ tests/test_control.c src/control.c src/metrics.c src/scheduler.c -lm -lpthread

layer: $(BUILD)/libVkLayer_gfg_pacer.so $(BUILD)/VkLayer_gfg_pacer.json

$(BUILD)/libVkLayer_gfg_pacer.so: $(LAYER_SRC) $(LAYER_HDR)
	@test -f $(VULKAN_HEADERS)/vulkan/vk_layer.h || { echo "Vulkan headers not found in $(VULKAN_HEADERS) (set VULKAN_HEADERS or run tests/setup_vulkan_deps.sh)"; exit 1; }
	mkdir -p $(BUILD)
	$(CC) $(CFLAGS) -fvisibility=hidden -I$(VULKAN_HEADERS) -shared -Wl,-z,defs -o $@ $(LAYER_SRC) -lm -lpthread

# Games run under the Steam Runtime (sniper: glibc 2.31) or the host's newer glibc, whichever
# is newer: the shipped library may not need any symbol newer than GLIBC_MAX.
GLIBC_MAX ?= 2.31
abi: $(BUILD)/libVkLayer_gfg_pacer.so
	@need=$$(objdump -T $< | grep -o 'GLIBC_[0-9.]*' | sed 's/GLIBC_//' | sort -V | tail -1); \
	echo "gfg-pacer needs glibc $$need (max $(GLIBC_MAX))"; \
	[ "$$(printf '%s\n%s\n' "$$need" "$(GLIBC_MAX)" | sort -V | tail -1)" = "$(GLIBC_MAX)" ] || \
	{ objdump -T $< | grep -E 'GLIBC_2\.(3[2-9]|[4-9][0-9])'; exit 1; }

# The manifest's library_path is relative: it sits next to the .so.
$(BUILD)/VkLayer_gfg_pacer.json: VkLayer_gfg_pacer.json
	mkdir -p $(BUILD)
	cp $< $@

$(BUILD)/test_layer: tests/test_layer.c src/control.c src/scheduler.c $(LAYER_HDR)
	@test -e $(VULKAN_LOADER_DIR)/libvulkan.so || { echo "Vulkan loader not found in $(VULKAN_LOADER_DIR) (set VULKAN_LOADER_DIR or run tests/setup_vulkan_deps.sh)"; exit 1; }
	mkdir -p $(BUILD)
	$(CC) $(CFLAGS) -I$(VULKAN_HEADERS) -o $@ tests/test_layer.c src/control.c src/scheduler.c \
		-L$(VULKAN_LOADER_DIR) -Wl,-rpath,$(VULKAN_LOADER_DIR) -lvulkan -lm -lpthread

integration: layer $(BUILD)/test_layer
	@test -f $(MOCK_ICD_JSON) || { echo "mock ICD manifest not found: $(MOCK_ICD_JSON) (set MOCK_ICD_JSON or run tests/setup_vulkan_deps.sh)"; exit 1; }
	MOCK_ICD_JSON=$(MOCK_ICD_JSON) tests/run_integration.sh $(BUILD)

# Test-only stand-in for VK_LAYER_MAKO_render (2x present generator), for the layer-order test.
$(BUILD)/fixtures/libVkLayer_MAKO_dummy.so: tests/fixtures/mako_dummy_layer.c
	@test -f $(VULKAN_HEADERS)/vulkan/vk_layer.h || { echo "Vulkan headers not found in $(VULKAN_HEADERS)"; exit 1; }
	mkdir -p $(BUILD)/fixtures
	$(CC) $(CFLAGS) -fvisibility=hidden -I$(VULKAN_HEADERS) -shared -Wl,-z,defs -o $@ $<

# Layer order: gfg-pacer must sit above the frame generator whatever the manifest readdir order.
# Extra loaders to check: ORDER_LOADER_DIRS="dir1 dir2" (default: the build loader).
ordering: layer $(BUILD)/test_layer $(BUILD)/fixtures/libVkLayer_MAKO_dummy.so
	@test -f $(MOCK_ICD_JSON) || { echo "mock ICD manifest not found: $(MOCK_ICD_JSON)"; exit 1; }
	MOCK_ICD_JSON=$(MOCK_ICD_JSON) ORDER_LOADER_DIRS="$(or $(ORDER_LOADER_DIRS),$(VULKAN_LOADER_DIR))" \
		tests/run_ordering.sh $(BUILD)

clean:
	rm -rf $(BUILD)
