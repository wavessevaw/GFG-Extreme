/* Exercise the real hot-path slot helpers with an intentionally busy GPU.
 *
 * Field report 1.3: the HUD flickered.  An overlay update waited (0 ns) for every image's previous
 * copy and skipped the whole HUD on that frame when one was still running, and an image whose own
 * copy was in flight skipped it too.  Now an update never touches fences, each image has two
 * slots, and only when both are in flight is the older one waited for, at most SLOT_WAIT_NS. */
#include "../src/layer.c"
#include <assert.h>

static unsigned waits, resets;
static uint64_t seen_timeout;
static VkFence busy_fence = VK_NULL_HANDLE;    /* this fence never signals (VK_NULL_HANDLE: none) */
static int all_busy = 0;

static VKAPI_ATTR VkResult VKAPI_CALL wait_fences(VkDevice device, uint32_t count,
        const VkFence *fences, VkBool32 all, uint64_t timeout)
{
    (void)device; (void)count; (void)all;
    waits++;
    seen_timeout = timeout;
    return (all_busy || fences[0] == busy_fence) ? VK_TIMEOUT : VK_SUCCESS;
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
    /* one image, two slots: both have their objects already (no creation in this test) */
    hud_slot slots[SLOTS_PER_IMAGE] = {
        { .submitted = 1, .fence = (VkFence)(uintptr_t)1, .sem = (VkSemaphore)(uintptr_t)11,
          .cmd = (VkCommandBuffer)(uintptr_t)21, .submit_seq = 1 },
        { .submitted = 1, .fence = (VkFence)(uintptr_t)2, .sem = (VkSemaphore)(uintptr_t)12,
          .cmd = (VkCommandBuffer)(uintptr_t)22, .submit_seq = 2 },
    };
    hud_swapchain sc = { .slots = slots, .image_count = 1 };
    VkResult r;
    d.WaitForFences = wait_fences;
    d.ResetFences = reset_fences;

    /* an overlay update never waits for copies in flight */
    assert(sc_update(&d, &sc, 1) == VK_SUCCESS);
    assert(waits == 0 && sc.have_gen);

    /* slot 0 still copying: slot 1 is used at once, no long wait */
    busy_fence = slots[0].fence;
    hud_slot *s = pick_slot(&d, &sc, 0, 0, &r);
    assert(s == &slots[1] && r == VK_SUCCESS && seen_timeout == FENCE_WAIT_NS);
    assert(!slots[1].submitted && slots[0].submitted);

    /* both in flight: only the older one is waited for, and only up to SLOT_WAIT_NS */
    slots[1].submitted = 1;
    slots[1].submit_seq = 3;
    all_busy = 1;
    waits = 0;
    s = pick_slot(&d, &sc, 0, 0, &r);
    assert(!s && r == VK_TIMEOUT && waits == 3 && seen_timeout == SLOT_WAIT_NS);

    /* the GPU catches up: the older slot (lower submit_seq) comes back first */
    all_busy = 0;
    busy_fence = VK_NULL_HANDLE;
    s = pick_slot(&d, &sc, 0, 0, &r);
    assert(s == &slots[0] && r == VK_SUCCESS);

    /* teardown still protects in-flight objects */
    slots[0].submitted = 1;
    assert(slot_wait(&d, &slots[0], DESTROY_WAIT_NS) == VK_SUCCESS);
    assert(seen_timeout == DESTROY_WAIT_NS);
    if (g_source_ready)
        gfg_hud_source_free(&g_source);
    puts("HUD busy GPU: no update waits, second slot, bounded wait passed");
    return 0;
}
