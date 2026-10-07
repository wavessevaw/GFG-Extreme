CC ?= gcc
CFLAGS ?= -std=c11 -O2 -Wall -Wextra -Werror -fPIC
BUILD := build

.PHONY: test clean
test: $(BUILD)/test_scheduler
	$(BUILD)/test_scheduler

$(BUILD)/test_scheduler: tests/test_scheduler.c src/scheduler.c src/scheduler.h
	mkdir -p $(BUILD)
	$(CC) $(CFLAGS) -o $@ tests/test_scheduler.c src/scheduler.c -lm

clean:
	rm -rf $(BUILD)
