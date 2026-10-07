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

.PHONY: test layer integration clean
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

clean:
	rm -rf $(BUILD)
