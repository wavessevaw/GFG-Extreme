/* Exercise the real hot-path fence helpers with an intentionally busy GPU. */
#include "../src/layer.c"
#include <assert.h>

static unsigned waits, resets;
static uint64_t seen_timeout;
static VkResult result = VK_TIMEOUT;

static VKAPI_ATTR VkResult VKAPI_CALL wait_fences(VkDevice device, uint32_t count,
        const VkFence *fences, VkBool32 all, uint64_t timeout)
{
    (void)device; (void)count; (void)fences; (void)all;
    waits++;
    seen_timeout = timeout;
    return result;
}

static VKAPI_ATTR VkResult VKAPI_CALL reset_fences(VkDevice device, uint32_t count, const VkFence *fences)
{
    (void)device; (void)count; (void)fences;
    resets++;
    return VK_SUCCESS;
}

int main(void)
{
    dev_data d = {0};
    hud_slot slot = { .submitted = 1, .fence = (VkFence)(uintptr_t)1 };
    hud_swapchain sc = { .slots = &slot, .image_count = 1 };
    d.WaitForFences = wait_fences;
    d.ResetFences = reset_fences;

    assert(slot_ready(&d, &slot, 0) == VK_TIMEOUT);
    assert(waits == 1 && seen_timeout == 0 && resets == 0 && slot.submitted);
    assert(sc_update(&d, &sc, 1) == VK_TIMEOUT);
    assert(waits == 2 && seen_timeout == 0 && resets == 0 && !sc.have_gen);

    result = VK_SUCCESS;
    assert(slot_wait(&d, &slot, FENCE_WAIT_NS) == VK_SUCCESS);
    assert(seen_timeout == 0 && resets == 1 && !slot.submitted);
    slot.submitted = 1;
    assert(slot_wait(&d, &slot, DESTROY_WAIT_NS) == VK_SUCCESS);
    assert(seen_timeout == DESTROY_WAIT_NS); /* teardown still protects in-flight objects */
    if (g_source_ready)
        gfg_hud_source_free(&g_source);
    puts("HUD busy GPU: nonblocking skip and recovery passed");
    return 0;
}
