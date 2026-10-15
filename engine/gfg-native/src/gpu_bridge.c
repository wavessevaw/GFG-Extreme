#define _GNU_SOURCE
/* SPDX-License-Identifier: GPL-3.0-or-later
 *
 * GFG Native GPU-resident transport for the TE8 generator (GFG_NATIVE_GPU_BRIDGE=1).
 *
 * No CPU pixel access and no CPU wait on the present path in steady state.
 * TE8 runs on its own VkDevice (same physical GPU, matched by deviceUUID); its
 * two source images and two destination images are exported as OPAQUE_FD
 * memory and imported into the APP's VkDevice with identical create info and
 * a dedicated allocation.
 *
 * Synchronization between the two devices is one timeline semaphore:
 *   real frame n gets the block V = 3n+1 .. V+2
 *   V   : app queue finished copying swapchain image n into TE source slot
 *   V+1 : TE finished synthetic output 0 (t = 1/3)
 *   V+2 : TE finished synthetic output 1 (t = 2/3) and all TE work of pair n
 * Shared mode: the timeline is created exportable on the app device and
 *   imported by TE (te_context_desc.sync_fd), so both GPUs wait/signal it.
 * Relay mode (no VK_KHR_external_semaphore_fd, e.g. lavapipe): two timelines,
 *   a relay THREAD (never the present thread) host-waits one and host-signals
 *   the other.  GPU work is still submitted wait-before-signal; the present
 *   thread never blocks.
 *
 * Present n (single swapchain, the app's present queue):
 *   1. submit: wait app semaphores (TRANSFER) + timeline >= last TE value,
 *      copy swapchain[idx] -> TE source slot (EXTERNAL ownership release),
 *      signal timeline V and ready[idx];
 *   2. te_submit_frame{slot, count 2, t {1/3, 2/3}, wait V, signal V+1, nonblocking};
 *   3. for k = 1, 2: acquire (timeout 0), submit: wait acquire semaphore +
 *      timeline >= V+k, copy/blit dest[k-1] -> image, signal ready[img]; present;
 *   4. forward the app's present with pWaitSemaphores = { ready[idx] }.
 * Screen order: G(n-2/3), G(n-1/3), R(n).
 *
 * Binary semaphore rule: every binary semaphore we signal is waited exactly
 * once (ready[idx] by the forwarded real present, ready[img] by its synthetic
 * present, the acquire semaphore by the synthetic copy).  Per-frame command
 * buffers and acquire semaphores live in a ring whose fences are only polled
 * (vkGetFenceStatus); a busy slot passes the real present through unmodified.
 */
#include "gpu_bridge.h"
#include "te_engine.h"
#include <pthread.h>
#include <stdatomic.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

#define RING_MAX 4
#define RELAY_CAP 8
#define TIMING_CAP 8192

#define FN(name) PFN_vk##name name
#define DEVICE_FUNCS(X) \
    X(CreateImage) X(DestroyImage) X(GetImageMemoryRequirements) X(AllocateMemory) \
    X(FreeMemory) X(BindImageMemory) X(CreateBuffer) X(DestroyBuffer) \
    X(GetBufferMemoryRequirements) X(BindBufferMemory) X(MapMemory) X(UnmapMemory) \
    X(InvalidateMappedMemoryRanges) \
    X(CreateCommandPool) X(DestroyCommandPool) X(AllocateCommandBuffers) \
    X(ResetCommandBuffer) X(BeginCommandBuffer) X(EndCommandBuffer) \
    X(CmdPipelineBarrier) X(CmdCopyImage) X(CmdBlitImage) X(CmdCopyImageToBuffer) \
    X(CreateSemaphore) X(DestroySemaphore) X(CreateFence) X(DestroyFence) \
    X(ResetFences) X(GetFenceStatus) X(WaitForFences) X(QueueSubmit) \
    X(GetSemaphoreCounterValue) X(SignalSemaphore) X(WaitSemaphores) \
    X(AcquireNextImageKHR) X(GetSwapchainImagesKHR)

typedef struct {
    VkImage image;
    VkDeviceMemory memory;
} imported_image;

typedef struct {
    VkCommandBuffer real_cb;
    VkCommandBuffer gen_cb[2];
    VkSemaphore acquire_sem[2];
    VkFence fence;
    int busy;
} ring_slot;

typedef struct {
    pthread_t thread;
    pthread_mutex_t lock;
    pthread_cond_t cond;
    uint64_t jobs[RELAY_CAP];
    uint32_t head, count;
    int stop, started, failed;
} relay_state;

struct gfg_gpu_fg {
    VkDevice device;
    VkQueue queue;
    VkSwapchainKHR swapchain;
    uint32_t family;
    VkExtent2D extent;
    VkFormat format;
    VkPresentModeKHR present_mode;
#define DECLARE(name) FN(name);
    DEVICE_FUNCS(DECLARE)
#undef DECLARE
    PFN_vkGetSemaphoreFdKHR GetSemaphoreFdKHR;
    PFN_vkSetDeviceLoaderData set_loader_data;
    VkPhysicalDeviceMemoryProperties memory_props;

    VkImage *images;
    uint32_t image_count;
    VkSemaphore *ready;          /* one binary semaphore per swapchain image */

    imported_image src[2], dst[2];
    int src_bgra;
    enum { OUT_COPY, OUT_BLIT, OUT_BLIT_COPY } out_mode;
    VkImage scratch;             /* OUT_BLIT_COPY: B8G8R8A8_UNORM swizzle target */
    VkDeviceMemory scratch_memory;

    VkSemaphore timeline;        /* app device: shared with TE or relayed */
    int shared_sync;
    relay_state relay;

    VkCommandPool pool;
    VkCommandBuffer init_cb;
    VkFence init_fence;
    ring_slot ring[RING_MAX];
    uint32_t ring_size;
    uint64_t frame;              /* real presents seen by this bridge */

    te_device *engine;
    te_context *context;
    uint32_t te_slot;            /* next source slot TE expects */
    uint64_t te_frames;          /* frames TE accepted */
    int te_gap;                  /* a frame since the last accepted one was not fed to TE */
    uint64_t next_value;         /* first value of the next block */
    uint64_t last_te_value;      /* last value TE (or the relay) will signal */
    int lmc_tier;

    /* test-only verification (GFG_NATIVE_GPU_BRIDGE_VERIFY=1) */
    int verify;
    uint32_t verify_every;
    VkImage verify_hist[2];      /* copies of the real frames (TE sources lack TRANSFER_SRC) */
    VkDeviceMemory verify_hist_memory[2];
    VkBuffer verify_buffer;
    VkDeviceMemory verify_memory;
    VkDeviceSize verify_bytes;
    int verify_coherent;
    VkCommandBuffer verify_cb;
    VkFence verify_fence;
    int verify_pending;
    uint64_t verify_frame;

    uint32_t inject_every;       /* test-only fault injection (GFG_NATIVE_GPU_BRIDGE_INJECT_SKIP) */
    int disabled;
    int log;
    int in_present;
    double *timing_total_us, *timing_own_us;
    /* per-phase CPU time sums (GFG_NATIVE_TIMING): record+submit real copy,
     * te_submit_frame, acquire, synthetic record+submit, fence submit */
    double phase_us[5];
    uint64_t phase_n;
    uint32_t timing_count;
};

static struct {
    atomic_uint_fast64_t v[sizeof(gfg_gpu_stats) / sizeof(uint64_t)];
} g_stats;
#define STAT_INDEX(field) (offsetof(gfg_gpu_stats, field) / sizeof(uint64_t))
#define STAT_ADD(field, n) atomic_fetch_add_explicit(&g_stats.v[STAT_INDEX(field)], (n), memory_order_relaxed)
#define STAT_SET(field, n) atomic_store_explicit(&g_stats.v[STAT_INDEX(field)], (n), memory_order_relaxed)

void gfg_gpu_fg_stats(gfg_gpu_stats *out) {
    if (!out) return;
    uint64_t *dst = (uint64_t *)out;
    for (size_t i = 0; i < sizeof(gfg_gpu_stats) / sizeof(uint64_t); ++i)
        dst[i] = atomic_load_explicit(&g_stats.v[i], memory_order_relaxed);
    out->version = 1;
}

static double now_us(void) {
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return (double)t.tv_sec * 1e6 + (double)t.tv_nsec / 1e3;
}
static int ok(VkResult r) { return r == VK_SUCCESS; }
static void fail_log(gfg_gpu_fg *fg, const char *what, VkResult r) {
    (void)fg;
    fprintf(stderr, "[gfg-native] gpu-bridge %s vkresult=%d\n", what, (int)r);
}

/* Every blocking wait goes through these so the counters prove the contract. */
static void count_wait(gfg_gpu_fg *fg) {
    if (fg->in_present) STAT_ADD(present_path_cpu_waits, 1);
    else STAT_ADD(teardown_cpu_waits, 1);
}
static VkResult wait_fence(gfg_gpu_fg *fg, VkFence fence, uint64_t timeout) {
    count_wait(fg);
    return fg->WaitForFences(fg->device, 1, &fence, VK_TRUE, timeout);
}

static int is_bgra(VkFormat f) {
    return f == VK_FORMAT_B8G8R8A8_UNORM || f == VK_FORMAT_B8G8R8A8_SRGB;
}
static int is_srgb(VkFormat f) {
    return f == VK_FORMAT_B8G8R8A8_SRGB || f == VK_FORMAT_R8G8B8A8_SRGB;
}
static int supported_format(VkFormat f) {
    return f == VK_FORMAT_B8G8R8A8_UNORM || f == VK_FORMAT_B8G8R8A8_SRGB ||
           f == VK_FORMAT_R8G8B8A8_UNORM || f == VK_FORMAT_R8G8B8A8_SRGB;
}

static int32_t find_memory(const VkPhysicalDeviceMemoryProperties *mp, uint32_t bits,
                           VkMemoryPropertyFlags want) {
    for (uint32_t i = 0; i < mp->memoryTypeCount; ++i)
        if ((bits & (1u << i)) && (mp->memoryTypes[i].propertyFlags & want) == want)
            return (int32_t)i;
    return -1;
}

/* Must mirror te_engine.c image_create() for imports: same format, usage,
 * tiling, extent, external handle type, dedicated allocation and the same
 * memory-type choice (first DEVICE_LOCAL type in the requirement bits). */
static int import_image(gfg_gpu_fg *fg, imported_image *im, VkFormat format,
                        VkImageUsageFlags usage, int fd) {
    if (fd < 0) return 0;
    VkExternalMemoryImageCreateInfo emi = {
        .sType = VK_STRUCTURE_TYPE_EXTERNAL_MEMORY_IMAGE_CREATE_INFO,
        .handleTypes = VK_EXTERNAL_MEMORY_HANDLE_TYPE_OPAQUE_FD_BIT};
    VkImageCreateInfo ici = {
        .sType = VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO, .pNext = &emi,
        .imageType = VK_IMAGE_TYPE_2D, .format = format,
        .extent = {fg->extent.width, fg->extent.height, 1}, .mipLevels = 1,
        .arrayLayers = 1, .samples = VK_SAMPLE_COUNT_1_BIT,
        .tiling = VK_IMAGE_TILING_OPTIMAL, .usage = usage,
        .sharingMode = VK_SHARING_MODE_EXCLUSIVE,
        .initialLayout = VK_IMAGE_LAYOUT_UNDEFINED};
    VkResult r = fg->CreateImage(fg->device, &ici, NULL, &im->image);
    if (!ok(r)) { close(fd); fail_log(fg, "import vkCreateImage", r); return 0; }
    VkMemoryRequirements req;
    fg->GetImageMemoryRequirements(fg->device, im->image, &req);
    int32_t type = find_memory(&fg->memory_props, req.memoryTypeBits,
                               VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT);
    if (type < 0) type = find_memory(&fg->memory_props, req.memoryTypeBits, 0);
    if (type < 0) { close(fd); return 0; }
    VkMemoryDedicatedAllocateInfo ded = {
        .sType = VK_STRUCTURE_TYPE_MEMORY_DEDICATED_ALLOCATE_INFO, .image = im->image};
    VkImportMemoryFdInfoKHR imp = {
        .sType = VK_STRUCTURE_TYPE_IMPORT_MEMORY_FD_INFO_KHR, .pNext = &ded,
        .handleType = VK_EXTERNAL_MEMORY_HANDLE_TYPE_OPAQUE_FD_BIT, .fd = fd};
    VkMemoryAllocateInfo mai = {
        .sType = VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO, .pNext = &imp,
        .allocationSize = req.size, .memoryTypeIndex = (uint32_t)type};
    r = fg->AllocateMemory(fg->device, &mai, NULL, &im->memory);
    if (!ok(r)) { close(fd); fail_log(fg, "import vkAllocateMemory", r); return 0; }
    /* fd ownership passed to the implementation */
    r = fg->BindImageMemory(fg->device, im->image, im->memory, 0);
    if (!ok(r)) { fail_log(fg, "import vkBindImageMemory", r); return 0; }
    return 1;
}

static int local_image(gfg_gpu_fg *fg, VkImage *image, VkDeviceMemory *memory,
                       VkFormat format, VkImageUsageFlags usage) {
    VkImageCreateInfo ici = {
        .sType = VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO,
        .imageType = VK_IMAGE_TYPE_2D, .format = format,
        .extent = {fg->extent.width, fg->extent.height, 1}, .mipLevels = 1,
        .arrayLayers = 1, .samples = VK_SAMPLE_COUNT_1_BIT,
        .tiling = VK_IMAGE_TILING_OPTIMAL, .usage = usage,
        .sharingMode = VK_SHARING_MODE_EXCLUSIVE,
        .initialLayout = VK_IMAGE_LAYOUT_UNDEFINED};
    if (!ok(fg->CreateImage(fg->device, &ici, NULL, image))) return 0;
    VkMemoryRequirements req;
    fg->GetImageMemoryRequirements(fg->device, *image, &req);
    int32_t type = find_memory(&fg->memory_props, req.memoryTypeBits,
                               VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT);
    if (type < 0) type = find_memory(&fg->memory_props, req.memoryTypeBits, 0);
    if (type < 0) return 0;
    VkMemoryAllocateInfo mai = {.sType = VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO,
        .allocationSize = req.size, .memoryTypeIndex = (uint32_t)type};
    if (!ok(fg->AllocateMemory(fg->device, &mai, NULL, memory))) return 0;
    return ok(fg->BindImageMemory(fg->device, *image, *memory, 0));
}

/* ------------------------------------------------------------ barriers */

static const VkImageSubresourceRange COLOR = {VK_IMAGE_ASPECT_COLOR_BIT, 0, 1, 0, 1};

static VkImageMemoryBarrier image_barrier(VkImage image, VkAccessFlags sa, VkAccessFlags da,
        VkImageLayout from, VkImageLayout to, uint32_t src_family, uint32_t dst_family) {
    VkImageMemoryBarrier b = {.sType = VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER,
        .srcAccessMask = sa, .dstAccessMask = da, .oldLayout = from, .newLayout = to,
        .srcQueueFamilyIndex = src_family, .dstQueueFamilyIndex = dst_family,
        .image = image, .subresourceRange = COLOR};
    return b;
}
static void cmd_barrier(gfg_gpu_fg *fg, VkCommandBuffer cb, VkPipelineStageFlags src,
                        VkPipelineStageFlags dst, uint32_t n, const VkImageMemoryBarrier *b) {
    fg->CmdPipelineBarrier(cb, src, dst, 0, 0, NULL, 0, NULL, n, b);
}
/* TE's contract (te_engine.c ownership()): images are in GENERAL; TE acquires
 * sources and destinations from VK_QUEUE_FAMILY_EXTERNAL with GENERAL->GENERAL
 * and releases destinations to EXTERNAL the same way.  We mirror that and use
 * GENERAL for our own copies so release/acquire layouts always match. */
static VkImageMemoryBarrier acquire_external(gfg_gpu_fg *fg, VkImage image, VkAccessFlags da) {
    return image_barrier(image, 0, da, VK_IMAGE_LAYOUT_GENERAL, VK_IMAGE_LAYOUT_GENERAL,
                         VK_QUEUE_FAMILY_EXTERNAL, fg->family);
}
static VkImageMemoryBarrier release_external(gfg_gpu_fg *fg, VkImage image, VkAccessFlags sa) {
    return image_barrier(image, sa, 0, VK_IMAGE_LAYOUT_GENERAL, VK_IMAGE_LAYOUT_GENERAL,
                         fg->family, VK_QUEUE_FAMILY_EXTERNAL);
}

/* Command buffers we allocate below the loader trampoline need the loader's
 * dispatch pointer, or layers between us and the ICD (validation) crash. */
static int alloc_cb(gfg_gpu_fg *fg, VkCommandBuffer *cb) {
    VkCommandBufferAllocateInfo cai = {.sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO,
        .commandPool = fg->pool, .level = VK_COMMAND_BUFFER_LEVEL_PRIMARY, .commandBufferCount = 1};
    if (!ok(fg->AllocateCommandBuffers(fg->device, &cai, cb))) return 0;
    if (fg->set_loader_data && !ok(fg->set_loader_data(fg->device, *cb))) return 0;
    return 1;
}

static int begin(gfg_gpu_fg *fg, VkCommandBuffer cb) {
    if (!ok(fg->ResetCommandBuffer(cb, 0))) return 0;
    VkCommandBufferBeginInfo bi = {.sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO,
        .flags = VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT};
    return ok(fg->BeginCommandBuffer(cb, &bi));
}

/* swapchain image (PRESENT_SRC, rendered by the app) -> TE source slot */
static int record_real(gfg_gpu_fg *fg, VkCommandBuffer cb, VkImage swap, VkImage slot,
                       VkImage hist) {
    if (!begin(fg, cb)) return 0;
    VkImageMemoryBarrier pre[2] = {
        /* the app's semaphores are waited at TRANSFER (B7): stage pairing explicit */
        image_barrier(swap, 0, VK_ACCESS_TRANSFER_READ_BIT, VK_IMAGE_LAYOUT_PRESENT_SRC_KHR,
                      VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL, VK_QUEUE_FAMILY_IGNORED,
                      VK_QUEUE_FAMILY_IGNORED),
        acquire_external(fg, slot, VK_ACCESS_TRANSFER_WRITE_BIT)};
    /* src TRANSFER also orders this write after earlier transfer reads of the
     * slot on this queue (verification copies) */
    cmd_barrier(fg, cb, VK_PIPELINE_STAGE_TRANSFER_BIT, VK_PIPELINE_STAGE_TRANSFER_BIT, 2, pre);
    VkImageCopy region = {.srcSubresource = {VK_IMAGE_ASPECT_COLOR_BIT, 0, 0, 1},
        .dstSubresource = {VK_IMAGE_ASPECT_COLOR_BIT, 0, 0, 1},
        .extent = {fg->extent.width, fg->extent.height, 1}};
    fg->CmdCopyImage(cb, swap, VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL, slot,
                     VK_IMAGE_LAYOUT_GENERAL, 1, &region);
    if (hist) { /* test-only verify mode: keep R(n) for the distinctness readback */
        VkImageMemoryBarrier h = image_barrier(hist, VK_ACCESS_TRANSFER_READ_BIT,
            VK_ACCESS_TRANSFER_WRITE_BIT, VK_IMAGE_LAYOUT_GENERAL, VK_IMAGE_LAYOUT_GENERAL,
            VK_QUEUE_FAMILY_IGNORED, VK_QUEUE_FAMILY_IGNORED);
        cmd_barrier(fg, cb, VK_PIPELINE_STAGE_TRANSFER_BIT, VK_PIPELINE_STAGE_TRANSFER_BIT, 1, &h);
        fg->CmdCopyImage(cb, swap, VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL, hist,
                         VK_IMAGE_LAYOUT_GENERAL, 1, &region);
    }
    VkImageMemoryBarrier post[2] = {
        image_barrier(swap, 0, 0, VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL,
                      VK_IMAGE_LAYOUT_PRESENT_SRC_KHR, VK_QUEUE_FAMILY_IGNORED,
                      VK_QUEUE_FAMILY_IGNORED),
        release_external(fg, slot, VK_ACCESS_TRANSFER_WRITE_BIT)};
    cmd_barrier(fg, cb, VK_PIPELINE_STAGE_TRANSFER_BIT, VK_PIPELINE_STAGE_BOTTOM_OF_PIPE_BIT, 2, post);
    return ok(fg->EndCommandBuffer(cb));
}

/* TE destination (R8G8B8A8_UNORM, GENERAL, EXTERNAL) -> acquired swapchain image */
static int record_generated(gfg_gpu_fg *fg, VkCommandBuffer cb, VkImage out, VkImage swap) {
    if (!begin(fg, cb)) return 0;
    VkImageMemoryBarrier pre[3] = {
        acquire_external(fg, out, VK_ACCESS_TRANSFER_READ_BIT),
        image_barrier(swap, 0, VK_ACCESS_TRANSFER_WRITE_BIT, VK_IMAGE_LAYOUT_UNDEFINED,
                      VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL, VK_QUEUE_FAMILY_IGNORED,
                      VK_QUEUE_FAMILY_IGNORED),
        /* scratch: previous use was a transfer on this queue */
        image_barrier(fg->scratch, VK_ACCESS_TRANSFER_READ_BIT | VK_ACCESS_TRANSFER_WRITE_BIT,
                      VK_ACCESS_TRANSFER_WRITE_BIT, VK_IMAGE_LAYOUT_GENERAL,
                      VK_IMAGE_LAYOUT_GENERAL, VK_QUEUE_FAMILY_IGNORED, VK_QUEUE_FAMILY_IGNORED)};
    cmd_barrier(fg, cb, VK_PIPELINE_STAGE_TRANSFER_BIT, VK_PIPELINE_STAGE_TRANSFER_BIT,
                fg->out_mode == OUT_BLIT_COPY ? 3u : 2u, pre);
    VkImageCopy copy = {.srcSubresource = {VK_IMAGE_ASPECT_COLOR_BIT, 0, 0, 1},
        .dstSubresource = {VK_IMAGE_ASPECT_COLOR_BIT, 0, 0, 1},
        .extent = {fg->extent.width, fg->extent.height, 1}};
    VkImageBlit blit = {.srcSubresource = {VK_IMAGE_ASPECT_COLOR_BIT, 0, 0, 1},
        .dstSubresource = {VK_IMAGE_ASPECT_COLOR_BIT, 0, 0, 1},
        .srcOffsets = {{0, 0, 0}, {(int32_t)fg->extent.width, (int32_t)fg->extent.height, 1}},
        .dstOffsets = {{0, 0, 0}, {(int32_t)fg->extent.width, (int32_t)fg->extent.height, 1}}};
    switch (fg->out_mode) {
    case OUT_COPY:   /* RGBA swapchain: raw bits, SRGB bytes pass through like the source copy */
        fg->CmdCopyImage(cb, out, VK_IMAGE_LAYOUT_GENERAL, swap,
                         VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL, 1, &copy);
        break;
    case OUT_BLIT:   /* RGBA_UNORM -> BGRA_UNORM: channel swizzle, no transfer function */
        fg->CmdBlitImage(cb, out, VK_IMAGE_LAYOUT_GENERAL, swap,
                         VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL, 1, &blit, VK_FILTER_NEAREST);
        break;
    case OUT_BLIT_COPY: { /* BGRA_SRGB: swizzle into UNORM scratch, then raw copy (no re-encode) */
        fg->CmdBlitImage(cb, out, VK_IMAGE_LAYOUT_GENERAL, fg->scratch,
                         VK_IMAGE_LAYOUT_GENERAL, 1, &blit, VK_FILTER_NEAREST);
        VkImageMemoryBarrier mid = image_barrier(fg->scratch, VK_ACCESS_TRANSFER_WRITE_BIT,
            VK_ACCESS_TRANSFER_READ_BIT, VK_IMAGE_LAYOUT_GENERAL, VK_IMAGE_LAYOUT_GENERAL,
            VK_QUEUE_FAMILY_IGNORED, VK_QUEUE_FAMILY_IGNORED);
        cmd_barrier(fg, cb, VK_PIPELINE_STAGE_TRANSFER_BIT, VK_PIPELINE_STAGE_TRANSFER_BIT, 1, &mid);
        fg->CmdCopyImage(cb, fg->scratch, VK_IMAGE_LAYOUT_GENERAL, swap,
                         VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL, 1, &copy);
        break; }
    }
    VkImageMemoryBarrier post[2] = {
        release_external(fg, out, 0),
        image_barrier(swap, VK_ACCESS_TRANSFER_WRITE_BIT, 0,
                      VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL, VK_IMAGE_LAYOUT_PRESENT_SRC_KHR,
                      VK_QUEUE_FAMILY_IGNORED, VK_QUEUE_FAMILY_IGNORED)};
    cmd_barrier(fg, cb, VK_PIPELINE_STAGE_TRANSFER_BIT, VK_PIPELINE_STAGE_BOTTOM_OF_PIPE_BIT, 2, post);
    return ok(fg->EndCommandBuffer(cb));
}

/* ------------------------------------------------------------ relay mode */

static VkResult app_timeline_wait(gfg_gpu_fg *fg, uint64_t value, uint64_t timeout) {
    VkSemaphoreWaitInfo wi = {.sType = VK_STRUCTURE_TYPE_SEMAPHORE_WAIT_INFO,
        .semaphoreCount = 1, .pSemaphores = &fg->timeline, .pValues = &value};
    return fg->WaitSemaphores(fg->device, &wi, timeout);
}
static VkResult app_timeline_signal(gfg_gpu_fg *fg, uint64_t value) {
    VkSemaphoreSignalInfo si = {.sType = VK_STRUCTURE_TYPE_SEMAPHORE_SIGNAL_INFO,
        .semaphore = fg->timeline, .value = value};
    return fg->SignalSemaphore(fg->device, &si);
}

/* Off the present thread: forwards V app->TE, then V+1, V+2 TE->app. */
static void *relay_main(void *arg) {
    gfg_gpu_fg *fg = arg;
    relay_state *rs = &fg->relay;
    const uint64_t slice = 50000000ull; /* 50 ms, re-checks stop */
    pthread_mutex_lock(&rs->lock);
    for (;;) {
        while (!rs->count && !rs->stop) pthread_cond_wait(&rs->cond, &rs->lock);
        if (!rs->count || rs->stop > 1) break;
        const uint64_t v = rs->jobs[rs->head];
        pthread_mutex_unlock(&rs->lock);
        VkResult r = VK_TIMEOUT;
        int step = 0;
        while (step < 3) {
            if (step == 0) r = app_timeline_wait(fg, v, slice);
            else r = te_timeline_wait(fg->context, v + (uint64_t)step, slice);
            if (r == VK_TIMEOUT) {
                pthread_mutex_lock(&rs->lock);
                int hard = rs->stop > 1;
                pthread_mutex_unlock(&rs->lock);
                if (hard) break;
                continue;
            }
            if (!ok(r)) break;
            r = step == 0 ? te_timeline_signal(fg->context, v)
                          : app_timeline_signal(fg, v + (uint64_t)step);
            if (!ok(r)) break;
            ++step;
        }
        pthread_mutex_lock(&rs->lock);
        if (step < 3) { rs->failed = 1; break; }
        rs->head = (rs->head + 1) % RELAY_CAP;
        --rs->count;
        pthread_cond_broadcast(&rs->cond);
    }
    pthread_cond_broadcast(&rs->cond);
    pthread_mutex_unlock(&rs->lock);
    return NULL;
}
static int relay_has_room(gfg_gpu_fg *fg) {
    relay_state *rs = &fg->relay;
    pthread_mutex_lock(&rs->lock);
    int room = rs->count < RELAY_CAP && !rs->failed && !rs->stop;
    pthread_mutex_unlock(&rs->lock);
    return room;
}
static void relay_push(gfg_gpu_fg *fg, uint64_t v) {
    relay_state *rs = &fg->relay;
    pthread_mutex_lock(&rs->lock);
    rs->jobs[(rs->head + rs->count) % RELAY_CAP] = v;
    ++rs->count;
    pthread_cond_signal(&rs->cond);
    pthread_mutex_unlock(&rs->lock);
}

/* ------------------------------------------------------------ verification */

static int verify_setup(gfg_gpu_fg *fg) {
    const VkFormat hist_format = fg->src_bgra ? VK_FORMAT_B8G8R8A8_UNORM : VK_FORMAT_R8G8B8A8_UNORM;
    for (int i = 0; i < 2; ++i)
        if (!local_image(fg, &fg->verify_hist[i], &fg->verify_hist_memory[i], hist_format,
                         VK_IMAGE_USAGE_TRANSFER_SRC_BIT | VK_IMAGE_USAGE_TRANSFER_DST_BIT))
            return 0;
    const VkDeviceSize one = (VkDeviceSize)fg->extent.width * fg->extent.height * 4u;
    fg->verify_bytes = one * 4u;
    VkBufferCreateInfo bi = {.sType = VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO,
        .size = fg->verify_bytes, .usage = VK_BUFFER_USAGE_TRANSFER_DST_BIT,
        .sharingMode = VK_SHARING_MODE_EXCLUSIVE};
    if (!ok(fg->CreateBuffer(fg->device, &bi, NULL, &fg->verify_buffer))) return 0;
    VkMemoryRequirements req;
    fg->GetBufferMemoryRequirements(fg->device, fg->verify_buffer, &req);
    int32_t type = find_memory(&fg->memory_props, req.memoryTypeBits,
        VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_CACHED_BIT);
    if (type < 0) type = find_memory(&fg->memory_props, req.memoryTypeBits,
        VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT);
    if (type < 0) return 0;
    fg->verify_coherent = !!(fg->memory_props.memoryTypes[type].propertyFlags &
                             VK_MEMORY_PROPERTY_HOST_COHERENT_BIT);
    VkMemoryAllocateInfo mai = {.sType = VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO,
        .allocationSize = req.size, .memoryTypeIndex = (uint32_t)type};
    if (!ok(fg->AllocateMemory(fg->device, &mai, NULL, &fg->verify_memory))) return 0;
    if (!ok(fg->BindBufferMemory(fg->device, fg->verify_buffer, fg->verify_memory, 0))) return 0;
    if (!alloc_cb(fg, &fg->verify_cb)) return 0;
    VkFenceCreateInfo fci = {.sType = VK_STRUCTURE_TYPE_FENCE_CREATE_INFO};
    return ok(fg->CreateFence(fg->device, &fci, NULL, &fg->verify_fence));
}

/* Copies G1, G2, R(n-1), R(n) to the host buffer; waits V+2 on the GPU only. */
static void verify_submit(gfg_gpu_fg *fg, uint64_t v, uint32_t cur_slot) {
    if (fg->verify_pending) return;
    VkCommandBuffer cb = fg->verify_cb;
    if (!begin(fg, cb)) return;
    VkImage imgs[4] = {fg->dst[0].image, fg->dst[1].image,
                       fg->verify_hist[cur_slot ^ 1u], fg->verify_hist[cur_slot]};
    VkImageMemoryBarrier acq[4], rel[2];
    for (int i = 0; i < 2; ++i) {
        acq[i] = acquire_external(fg, imgs[i], VK_ACCESS_TRANSFER_READ_BIT);
        rel[i] = release_external(fg, imgs[i], 0);
    }
    for (int i = 2; i < 4; ++i)
        acq[i] = image_barrier(imgs[i], VK_ACCESS_TRANSFER_WRITE_BIT, VK_ACCESS_TRANSFER_READ_BIT,
            VK_IMAGE_LAYOUT_GENERAL, VK_IMAGE_LAYOUT_GENERAL,
            VK_QUEUE_FAMILY_IGNORED, VK_QUEUE_FAMILY_IGNORED);
    /* the global barrier orders this write of the readback buffer after the
     * previous verification's write (WAW; the host already consumed it) */
    VkMemoryBarrier waw = {.sType = VK_STRUCTURE_TYPE_MEMORY_BARRIER,
        .srcAccessMask = VK_ACCESS_TRANSFER_WRITE_BIT, .dstAccessMask = VK_ACCESS_TRANSFER_WRITE_BIT};
    fg->CmdPipelineBarrier(cb, VK_PIPELINE_STAGE_TRANSFER_BIT, VK_PIPELINE_STAGE_TRANSFER_BIT, 0,
                           1, &waw, 0, NULL, 4, acq);
    const VkDeviceSize one = (VkDeviceSize)fg->extent.width * fg->extent.height * 4u;
    for (int i = 0; i < 4; ++i) {
        VkBufferImageCopy region = {.bufferOffset = one * (VkDeviceSize)i,
            .imageSubresource = {VK_IMAGE_ASPECT_COLOR_BIT, 0, 0, 1},
            .imageExtent = {fg->extent.width, fg->extent.height, 1}};
        fg->CmdCopyImageToBuffer(cb, imgs[i], VK_IMAGE_LAYOUT_GENERAL, fg->verify_buffer, 1, &region);
    }
    cmd_barrier(fg, cb, VK_PIPELINE_STAGE_TRANSFER_BIT, VK_PIPELINE_STAGE_BOTTOM_OF_PIPE_BIT, 2, rel);
    VkMemoryBarrier host = {.sType = VK_STRUCTURE_TYPE_MEMORY_BARRIER,
        .srcAccessMask = VK_ACCESS_TRANSFER_WRITE_BIT, .dstAccessMask = VK_ACCESS_HOST_READ_BIT};
    fg->CmdPipelineBarrier(cb, VK_PIPELINE_STAGE_TRANSFER_BIT, VK_PIPELINE_STAGE_HOST_BIT, 0,
                           1, &host, 0, NULL, 0, NULL);
    if (!ok(fg->EndCommandBuffer(cb))) return;
    const uint64_t wait_value = v + 2;
    VkTimelineSemaphoreSubmitInfo tsi = {.sType = VK_STRUCTURE_TYPE_TIMELINE_SEMAPHORE_SUBMIT_INFO,
        .waitSemaphoreValueCount = 1, .pWaitSemaphoreValues = &wait_value};
    const VkPipelineStageFlags stage = VK_PIPELINE_STAGE_TRANSFER_BIT;
    VkSubmitInfo si = {.sType = VK_STRUCTURE_TYPE_SUBMIT_INFO, .pNext = &tsi,
        .waitSemaphoreCount = 1, .pWaitSemaphores = &fg->timeline, .pWaitDstStageMask = &stage,
        .commandBufferCount = 1, .pCommandBuffers = &cb};
    if (!ok(fg->ResetFences(fg->device, 1, &fg->verify_fence))) return;
    if (!ok(fg->QueueSubmit(fg->queue, 1, &si, fg->verify_fence))) return;
    fg->verify_pending = 1;
    fg->verify_frame = fg->frame;
}

static uint64_t rgb_delta(const uint8_t *a, int a_bgra, const uint8_t *b, int b_bgra, size_t px) {
    uint64_t sum = 0;
    for (size_t i = 0; i < px; ++i) {
        for (int c = 0; c < 3; ++c) {
            int ca = a[4 * i + (a_bgra ? 2 - c : c)];
            int cb = b[4 * i + (b_bgra ? 2 - c : c)];
            sum += (uint64_t)(ca > cb ? ca - cb : cb - ca);
        }
    }
    return sum;
}

/* Non-blocking unless final (teardown). Host reads here are test-only. */
static void verify_collect(gfg_gpu_fg *fg, int final) {
    if (!fg->verify_pending) return;
    VkResult r = final ? wait_fence(fg, fg->verify_fence, 2000000000ull)
                       : fg->GetFenceStatus(fg->device, fg->verify_fence);
    if (r != VK_SUCCESS) return;
    fg->verify_pending = 0;
    void *map = NULL;
    if (!ok(fg->MapMemory(fg->device, fg->verify_memory, 0, VK_WHOLE_SIZE, 0, &map))) return;
    if (!fg->verify_coherent) {
        VkMappedMemoryRange range = {.sType = VK_STRUCTURE_TYPE_MAPPED_MEMORY_RANGE,
            .memory = fg->verify_memory, .size = VK_WHOLE_SIZE};
        fg->InvalidateMappedMemoryRanges(fg->device, 1, &range);
    }
    STAT_ADD(verify_host_reads, 1);
    const size_t px = (size_t)fg->extent.width * fg->extent.height;
    const uint8_t *g1 = map, *g2 = g1 + px * 4, *rp = g2 + px * 4, *rn = rp + px * 4;
    const int sb = fg->src_bgra;
    uint64_t d12 = rgb_delta(g1, 0, g2, 0, px);
    uint64_t d1p = rgb_delta(g1, 0, rp, sb, px), d1n = rgb_delta(g1, 0, rn, sb, px);
    uint64_t d2p = rgb_delta(g2, 0, rp, sb, px), d2n = rgb_delta(g2, 0, rn, sb, px);
    uint64_t dpn = rgb_delta(rp, sb, rn, sb, px);
    int distinct = d12 && d1p && d1n && d2p && d2n;
    /* interpolation sanity: G1 nearer R(n-1), G2 nearer R(n) */
    int ordered = d1p < d1n && d2n < d2p;
    fg->UnmapMemory(fg->device, fg->verify_memory);
    STAT_ADD(verify_checks, 1);
    if (distinct) STAT_ADD(verify_distinct, 1);
    fprintf(stderr,
        "[gfg-native] gpu-verify frame=%llu distinct=%d ordered=%d mad_g1g2=%.3f"
        " mad_g1_prev=%.3f mad_g1_real=%.3f mad_g2_prev=%.3f mad_g2_real=%.3f"
        " mad_prev_real=%.3f\n",
        (unsigned long long)fg->verify_frame, distinct, ordered,
        (double)d12 / (double)(px * 3), (double)d1p / (double)(px * 3),
        (double)d1n / (double)(px * 3), (double)d2p / (double)(px * 3),
        (double)d2n / (double)(px * 3), (double)dpn / (double)(px * 3));
}

/* ------------------------------------------------------------ lifecycle */

static int env_flag(const char *name) {
    const char *v = getenv(name);
    return v && v[0] == '1' && v[1] == '\0';
}
static unsigned env_uint(const char *name, unsigned def, unsigned lo, unsigned hi) {
    const char *v = getenv(name);
    if (!v || !*v) return def;
    char *end = NULL;
    unsigned long x = strtoul(v, &end, 10);
    if (!end || *end || x < lo || x > hi) return def;
    return (unsigned)x;
}

gfg_gpu_fg *gfg_gpu_fg_create(const gfg_gpu_fg_create_info *info) {
    if (!info || !info->device || !info->queue || !info->gdpa || !info->gipa ||
        !info->physical || !supported_format(info->format) ||
        info->extent.width < 16 || info->extent.height < 16 ||
        info->extent.width > 8192 || info->extent.height > 8192)
        return NULL;
    gfg_gpu_fg *fg = calloc(1, sizeof(*fg));
    if (!fg) return NULL;
    const double t0 = now_us();
    fg->device = info->device;
    fg->queue = info->queue;
    fg->swapchain = info->swapchain;
    fg->family = info->family;
    fg->extent = info->extent;
    fg->format = info->format;
    fg->present_mode = info->present_mode;
    fg->set_loader_data = info->set_loader_data;
    fg->log = getenv("GFG_NATIVE_TRACE") != NULL;
    fg->src_bgra = is_bgra(info->format);
    pthread_mutex_init(&fg->relay.lock, NULL);
    pthread_cond_init(&fg->relay.cond, NULL);
    const char *why = "entrypoints";
#define LOAD(name) fg->name = (PFN_vk##name)info->gdpa(info->device, "vk" #name); \
    if (!fg->name) goto fail;
    DEVICE_FUNCS(LOAD)
#undef LOAD
    fg->GetSemaphoreFdKHR = (PFN_vkGetSemaphoreFdKHR)info->gdpa(info->device, "vkGetSemaphoreFdKHR");
    PFN_vkGetPhysicalDeviceMemoryProperties mp = (PFN_vkGetPhysicalDeviceMemoryProperties)
        info->gipa(info->instance, "vkGetPhysicalDeviceMemoryProperties");
    PFN_vkGetPhysicalDeviceProperties2 props2 = (PFN_vkGetPhysicalDeviceProperties2)
        info->gipa(info->instance, "vkGetPhysicalDeviceProperties2");
    if (!props2) props2 = (PFN_vkGetPhysicalDeviceProperties2)
        info->gipa(info->instance, "vkGetPhysicalDeviceProperties2KHR");
    PFN_vkGetPhysicalDeviceFormatProperties fp = (PFN_vkGetPhysicalDeviceFormatProperties)
        info->gipa(info->instance, "vkGetPhysicalDeviceFormatProperties");
    if (!mp || !props2 || !fp) goto fail;
    mp(info->physical, &fg->memory_props);

    why = "output-format";
    if (!fg->src_bgra) {
        fg->out_mode = OUT_COPY;
    } else {
        VkFormatProperties rgba, bgra;
        fp(info->physical, VK_FORMAT_R8G8B8A8_UNORM, &rgba);
        fp(info->physical, VK_FORMAT_B8G8R8A8_UNORM, &bgra);
        if (!(rgba.optimalTilingFeatures & VK_FORMAT_FEATURE_BLIT_SRC_BIT) ||
            !(bgra.optimalTilingFeatures & VK_FORMAT_FEATURE_BLIT_DST_BIT))
            goto fail;
        fg->out_mode = is_srgb(info->format) ? OUT_BLIT_COPY : OUT_BLIT;
    }

    why = "swapchain-images";
    uint32_t n = 0;
    if (!ok(fg->GetSwapchainImagesKHR(fg->device, fg->swapchain, &n, NULL)) || n < 2 || n > 64)
        goto fail;
    fg->images = calloc(n, sizeof(*fg->images));
    fg->ready = calloc(n, sizeof(*fg->ready));
    if (!fg->images || !fg->ready ||
        !ok(fg->GetSwapchainImagesKHR(fg->device, fg->swapchain, &n, fg->images)))
        goto fail;
    fg->image_count = n;
    VkSemaphoreCreateInfo bsci = {.sType = VK_STRUCTURE_TYPE_SEMAPHORE_CREATE_INFO};
    for (uint32_t i = 0; i < n; ++i)
        if (!ok(fg->CreateSemaphore(fg->device, &bsci, NULL, &fg->ready[i]))) goto fail;

    /* TE on its own device, same GPU */
    why = "te-device";
    VkPhysicalDeviceIDProperties id = {.sType = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_ID_PROPERTIES};
    VkPhysicalDeviceProperties2 p2 = {.sType = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_PROPERTIES_2,
        .pNext = &id};
    props2(info->physical, &p2);
    te_device_desc dd = {.match_uuid = 1, .validation = env_flag("GFG_NATIVE_TE_VALIDATION")};
    memcpy(dd.device_uuid, id.deviceUUID, VK_UUID_SIZE);
    if (te_device_create(&dd, &fg->engine) != VK_SUCCESS) {
        fprintf(stderr, "[gfg-native] gpu-bridge TE device: %s\n", te_last_error());
        goto fail;
    }
    int te_mem = 0, te_sem = 0;
    te_device_supports_fd_import(fg->engine, &te_mem, &te_sem);
    why = "te-memory-fd";
    if (!te_mem) goto fail;
    const char *force_relay = getenv("GFG_NATIVE_GPU_SYNC");
    fg->shared_sync = info->semaphore_fd && te_sem && fg->GetSemaphoreFdKHR &&
                      !(force_relay && !strcmp(force_relay, "relay"));

    /* timeline on the app device: exportable in shared mode */
    why = "timeline";
    VkExportSemaphoreCreateInfo esci = {.sType = VK_STRUCTURE_TYPE_EXPORT_SEMAPHORE_CREATE_INFO,
        .handleTypes = VK_EXTERNAL_SEMAPHORE_HANDLE_TYPE_OPAQUE_FD_BIT};
    VkSemaphoreTypeCreateInfo stci = {.sType = VK_STRUCTURE_TYPE_SEMAPHORE_TYPE_CREATE_INFO,
        .pNext = fg->shared_sync ? &esci : NULL,
        .semaphoreType = VK_SEMAPHORE_TYPE_TIMELINE, .initialValue = 0};
    VkSemaphoreCreateInfo tsci = {.sType = VK_STRUCTURE_TYPE_SEMAPHORE_CREATE_INFO, .pNext = &stci};
    if (!ok(fg->CreateSemaphore(fg->device, &tsci, NULL, &fg->timeline))) goto fail;
    int sync_fd = -1;
    if (fg->shared_sync) {
        VkSemaphoreGetFdInfoKHR gi = {.sType = VK_STRUCTURE_TYPE_SEMAPHORE_GET_FD_INFO_KHR,
            .semaphore = fg->timeline, .handleType = VK_EXTERNAL_SEMAPHORE_HANDLE_TYPE_OPAQUE_FD_BIT};
        if (!ok(fg->GetSemaphoreFdKHR(fg->device, &gi, &sync_fd)) || sync_fd < 0) goto fail;
    }

    why = "te-context";
    te_context_desc cd;
    te_context_desc_default(&cd, fg->extent.width, fg->extent.height, 2);
    const char *algorithm = getenv("GFG_NATIVE_ALGO");
    cd.params.algorithm = (!algorithm || strcmp(algorithm, "lmc")) ? TE_ALGO_TILES : TE_ALGO_LMC;
    cd.export_fds = 1;
    cd.host_io = 0;
    cd.source_bgra = fg->src_bgra;
    cd.sync_fd = sync_fd; /* ownership passes to TE (closed on failure too) */
    if (te_context_create(fg->engine, &cd, &fg->context) != VK_SUCCESS) {
        fprintf(stderr, "[gfg-native] gpu-bridge TE context: %s\n", te_last_error());
        goto fail;
    }
    const char *tier = getenv("GFG_NATIVE_LMC_TIER");
    if (tier && tier[0] >= '0' && tier[0] <= '2' && tier[1] == '\0') fg->lmc_tier = tier[0] - '0';

    why = "import";
    const VkFormat src_format = fg->src_bgra ? VK_FORMAT_B8G8R8A8_UNORM : VK_FORMAT_R8G8B8A8_UNORM;
    for (uint32_t s = 0; s < 2; ++s)
        if (!import_image(fg, &fg->src[s], src_format,
                VK_IMAGE_USAGE_SAMPLED_BIT | VK_IMAGE_USAGE_TRANSFER_DST_BIT,
                te_export_source_fd(fg->context, s)))
            goto fail;
    /* TE-created (exported) destinations add TRANSFER_SRC; must match exactly */
    for (uint32_t o = 0; o < 2; ++o)
        if (!import_image(fg, &fg->dst[o], VK_FORMAT_R8G8B8A8_UNORM,
                VK_IMAGE_USAGE_STORAGE_BIT | VK_IMAGE_USAGE_SAMPLED_BIT |
                VK_IMAGE_USAGE_TRANSFER_SRC_BIT,
                te_export_dest_fd(fg->context, o)))
            goto fail;
    if (fg->out_mode == OUT_BLIT_COPY &&
        !local_image(fg, &fg->scratch, &fg->scratch_memory, VK_FORMAT_B8G8R8A8_UNORM,
                     VK_IMAGE_USAGE_TRANSFER_SRC_BIT | VK_IMAGE_USAGE_TRANSFER_DST_BIT))
        goto fail;

    why = "commands";
    VkCommandPoolCreateInfo pci = {.sType = VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO,
        .flags = VK_COMMAND_POOL_CREATE_RESET_COMMAND_BUFFER_BIT, .queueFamilyIndex = fg->family};
    if (!ok(fg->CreateCommandPool(fg->device, &pci, NULL, &fg->pool))) goto fail;
    fg->ring_size = env_uint("GFG_NATIVE_GPU_INFLIGHT", 2, 1, RING_MAX);
    VkFenceCreateInfo fci = {.sType = VK_STRUCTURE_TYPE_FENCE_CREATE_INFO};
    for (uint32_t r = 0; r < fg->ring_size; ++r) {
        ring_slot *rs = &fg->ring[r];
        if (!alloc_cb(fg, &rs->real_cb)) goto fail;
        for (int k = 0; k < 2; ++k) {
            if (!alloc_cb(fg, &rs->gen_cb[k])) goto fail;
            if (!ok(fg->CreateSemaphore(fg->device, &bsci, NULL, &rs->acquire_sem[k]))) goto fail;
        }
        if (!ok(fg->CreateFence(fg->device, &fci, NULL, &rs->fence))) goto fail;
    }
    if (!alloc_cb(fg, &fg->init_cb)) goto fail;
    if (!ok(fg->CreateFence(fg->device, &fci, NULL, &fg->init_fence))) goto fail;

    fg->verify = env_flag("GFG_NATIVE_GPU_BRIDGE_VERIFY");
    fg->verify_every = env_uint("GFG_NATIVE_GPU_BRIDGE_VERIFY_EVERY", 8, 1, 100000);
    fg->inject_every = env_uint("GFG_NATIVE_GPU_BRIDGE_INJECT_SKIP", 0, 2, 100000);
    why = "verify";
    if (fg->verify && !verify_setup(fg)) goto fail;

    /* One-time: give our side of the shared images a defined GENERAL layout
     * and hand them to EXTERNAL (TE acquires GENERAL->GENERAL). No CPU wait:
     * queue order puts it before the first real copy. */
    if (!begin(fg, fg->init_cb)) goto fail;
    {
        VkImage shared[4] = {fg->src[0].image, fg->src[1].image, fg->dst[0].image, fg->dst[1].image};
        VkImageMemoryBarrier tr[7], rel[4];
        uint32_t nt = 0;
        for (int i = 0; i < 4; ++i) {
            tr[nt++] = image_barrier(shared[i], 0, 0, VK_IMAGE_LAYOUT_UNDEFINED,
                VK_IMAGE_LAYOUT_GENERAL, VK_QUEUE_FAMILY_IGNORED, VK_QUEUE_FAMILY_IGNORED);
            rel[i] = release_external(fg, shared[i], 0);
        }
        if (fg->scratch)
            tr[nt++] = image_barrier(fg->scratch, 0, VK_ACCESS_TRANSFER_WRITE_BIT,
                VK_IMAGE_LAYOUT_UNDEFINED, VK_IMAGE_LAYOUT_GENERAL,
                VK_QUEUE_FAMILY_IGNORED, VK_QUEUE_FAMILY_IGNORED);
        for (int i = 0; i < 2; ++i)
            if (fg->verify_hist[i])
                tr[nt++] = image_barrier(fg->verify_hist[i], 0, VK_ACCESS_TRANSFER_WRITE_BIT,
                    VK_IMAGE_LAYOUT_UNDEFINED, VK_IMAGE_LAYOUT_GENERAL,
                    VK_QUEUE_FAMILY_IGNORED, VK_QUEUE_FAMILY_IGNORED);
        cmd_barrier(fg, fg->init_cb, VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT,
                    VK_PIPELINE_STAGE_TRANSFER_BIT, nt, tr);
        cmd_barrier(fg, fg->init_cb, VK_PIPELINE_STAGE_TRANSFER_BIT,
                    VK_PIPELINE_STAGE_BOTTOM_OF_PIPE_BIT, 4, rel);
    }
    if (!ok(fg->EndCommandBuffer(fg->init_cb))) goto fail;
    VkSubmitInfo isi = {.sType = VK_STRUCTURE_TYPE_SUBMIT_INFO, .commandBufferCount = 1,
        .pCommandBuffers = &fg->init_cb};
    if (!ok(fg->QueueSubmit(fg->queue, 1, &isi, fg->init_fence))) goto fail;


    if (!fg->shared_sync) {
        why = "relay-thread";
        if (pthread_create(&fg->relay.thread, NULL, relay_main, fg) != 0) goto fail;
        fg->relay.started = 1;
    }
    fg->next_value = 1;
    fg->timing_total_us = calloc(TIMING_CAP, sizeof(double));
    fg->timing_own_us = calloc(TIMING_CAP, sizeof(double));
    STAT_ADD(bridges_created, 1);
    STAT_SET(sync_mode, fg->shared_sync ? 1 : 2);
    fprintf(stderr,
        "[gfg-native] GPU bridge active: %ux%u format=%d out=%s sync=%s images=%u"
        " present_mode=%d inflight=%u algo=%s verify=%d startup_ms=%.2f\n",
        fg->extent.width, fg->extent.height, (int)fg->format,
        fg->out_mode == OUT_COPY ? "copy" : fg->out_mode == OUT_BLIT ? "blit" : "blit+copy",
        fg->shared_sync ? "shared-timeline-fd" : "host-relay", fg->image_count,
        (int)fg->present_mode, fg->ring_size,
        cd.params.algorithm == TE_ALGO_LMC ? "lmc" : "tiles", fg->verify,
        (now_us() - t0) / 1000.0);
    if (fg->present_mode != VK_PRESENT_MODE_FIFO_KHR &&
        fg->present_mode != VK_PRESENT_MODE_FIFO_RELAXED_KHR)
        fprintf(stderr, "[gfg-native] gpu-bridge WARNING present_mode=%d is not FIFO:"
                " synthetic frames are not paced by vblank backpressure\n",
                (int)fg->present_mode);
    return fg;
fail:
    fprintf(stderr, "[gfg-native] GPU bridge unavailable stage=%s\n", why);
    gfg_gpu_fg_destroy(fg);
    return NULL;
}

static int cmp_double(const void *a, const void *b) {
    double x = *(const double *)a, y = *(const double *)b;
    return x < y ? -1 : x > y;
}
static void percentile(double *v, uint32_t n, double *median, double *p95) {
    qsort(v, n, sizeof(double), cmp_double);
    *median = n ? v[n / 2] : 0.0;
    *p95 = n ? v[(uint32_t)((n - 1) * 0.95)] : 0.0;
}

void gfg_gpu_fg_destroy(gfg_gpu_fg *fg) {
    if (!fg) return;
    fg->in_present = 0;
    /* Relay: drain what the GPU will still signal, then stop. */
    if (fg->relay.started) {
        relay_state *rs = &fg->relay;
        struct timespec until;
        clock_gettime(CLOCK_REALTIME, &until);
        until.tv_sec += 3;
        pthread_mutex_lock(&rs->lock);
        while (rs->count && !rs->failed &&
               pthread_cond_timedwait(&rs->cond, &rs->lock, &until) == 0) {}
        rs->stop = rs->count ? 2 : 1;
        pthread_cond_broadcast(&rs->cond);
        pthread_mutex_unlock(&rs->lock);
        STAT_ADD(teardown_cpu_waits, 1);
        pthread_join(rs->thread, NULL);
    }
    if (fg->device && fg->timeline && fg->GetSemaphoreCounterValue && !fg->shared_sync) {
        /* never leave a GPU wait on a value nobody will signal */
        uint64_t cur = 0;
        if (ok(fg->GetSemaphoreCounterValue(fg->device, fg->timeline, &cur)) &&
            cur < fg->next_value + 3)
            (void)app_timeline_signal(fg, fg->next_value + 3);
        if (fg->context) (void)te_timeline_signal(fg->context, fg->next_value + 3);
    }
    if (fg->verify) verify_collect(fg, 1);
    if (fg->device && fg->WaitForFences) {
        if (fg->init_fence && fg->init_cb) (void)wait_fence(fg, fg->init_fence, 2000000000ull);
        for (uint32_t r = 0; r < fg->ring_size; ++r)
            if (fg->ring[r].busy) (void)wait_fence(fg, fg->ring[r].fence, 2000000000ull);
    }
    gfg_gpu_stats st;
    gfg_gpu_fg_stats(&st);
    if (fg->log || getenv("GFG_NATIVE_TIMING")) {
        fprintf(stderr,
            "[gfg-native] GPU bridge retired real=%llu synthetic=%llu skipped=%llu te_busy=%llu"
            " ring_busy=%llu acquire_not_ready=%llu holds=%llu errors=%llu"
            " present_path_host_pixel_reads=%llu present_path_cpu_waits=%llu"
            " verify_checks=%llu verify_distinct=%llu\n",
            (unsigned long long)st.real_presents, (unsigned long long)st.synthetic_presents,
            (unsigned long long)st.skipped_synthetic, (unsigned long long)st.te_busy,
            (unsigned long long)st.ring_busy, (unsigned long long)st.acquire_not_ready,
            (unsigned long long)st.holds, (unsigned long long)st.errors,
            (unsigned long long)st.present_path_host_pixel_reads,
            (unsigned long long)st.present_path_cpu_waits,
            (unsigned long long)st.verify_checks, (unsigned long long)st.verify_distinct);
        if (fg->timing_total_us && fg->timing_count > 2) {
            /* first two frames carry one-time work (TE warm-up); excluded */
            uint32_t n = fg->timing_count - 2;
            double tm, tp, om, op;
            percentile(fg->timing_total_us + 2, n, &tm, &tp);
            percentile(fg->timing_own_us + 2, n, &om, &op);
            fprintf(stderr,
                "[gfg-native] gpu-bridge present_cpu frames=%u %ux%u total_median_us=%.1f"
                " total_p95_us=%.1f layer_own_median_us=%.1f layer_own_p95_us=%.1f\n",
                n, fg->extent.width, fg->extent.height, tm, tp, om, op);
            if (fg->phase_n) {
                const double d = (double)fg->phase_n;
                fprintf(stderr,
                    "[gfg-native] gpu-bridge phase_mean_us real_submit=%.1f te_submit=%.1f"
                    " acquire=%.1f synthetic_submit=%.1f fence_submit=%.1f\n",
                    fg->phase_us[0] / d, fg->phase_us[1] / d, fg->phase_us[2] / d,
                    fg->phase_us[3] / d, fg->phase_us[4] / d);
            }
        }
    }
    if (fg->context) te_context_destroy(fg->context);
    if (fg->context && fg->engine && getenv("GFG_NATIVE_TE_VALIDATION"))
        fprintf(stderr, "[gfg-native] gpu-bridge TE validation_errors=%u\n",
                te_device_validation_errors(fg->engine));
    if (fg->engine) te_device_destroy(fg->engine);
    if (fg->device && fg->DestroySemaphore) {
        if (fg->ready)
            for (uint32_t i = 0; i < fg->image_count; ++i)
                if (fg->ready[i]) fg->DestroySemaphore(fg->device, fg->ready[i], NULL);
        for (uint32_t r = 0; r < RING_MAX; ++r)
            for (int k = 0; k < 2; ++k)
                if (fg->ring[r].acquire_sem[k])
                    fg->DestroySemaphore(fg->device, fg->ring[r].acquire_sem[k], NULL);
        if (fg->timeline) fg->DestroySemaphore(fg->device, fg->timeline, NULL);
    }
    if (fg->device && fg->DestroyFence) {
        for (uint32_t r = 0; r < RING_MAX; ++r)
            if (fg->ring[r].fence) fg->DestroyFence(fg->device, fg->ring[r].fence, NULL);
        if (fg->init_fence) fg->DestroyFence(fg->device, fg->init_fence, NULL);
        if (fg->verify_fence) fg->DestroyFence(fg->device, fg->verify_fence, NULL);
    }
    if (fg->device && fg->DestroyCommandPool && fg->pool)
        fg->DestroyCommandPool(fg->device, fg->pool, NULL);
    if (fg->device && fg->DestroyImage && fg->FreeMemory) {
        for (int i = 0; i < 2; ++i) {
            if (fg->src[i].image) fg->DestroyImage(fg->device, fg->src[i].image, NULL);
            if (fg->src[i].memory) fg->FreeMemory(fg->device, fg->src[i].memory, NULL);
            if (fg->dst[i].image) fg->DestroyImage(fg->device, fg->dst[i].image, NULL);
            if (fg->dst[i].memory) fg->FreeMemory(fg->device, fg->dst[i].memory, NULL);
        }
        if (fg->scratch) fg->DestroyImage(fg->device, fg->scratch, NULL);
        for (int i = 0; i < 2; ++i) {
            if (fg->verify_hist[i]) fg->DestroyImage(fg->device, fg->verify_hist[i], NULL);
            if (fg->verify_hist_memory[i]) fg->FreeMemory(fg->device, fg->verify_hist_memory[i], NULL);
        }
        if (fg->scratch_memory) fg->FreeMemory(fg->device, fg->scratch_memory, NULL);
    }
    if (fg->device && fg->DestroyBuffer && fg->verify_buffer)
        fg->DestroyBuffer(fg->device, fg->verify_buffer, NULL);
    if (fg->device && fg->FreeMemory && fg->verify_memory)
        fg->FreeMemory(fg->device, fg->verify_memory, NULL);
    pthread_mutex_destroy(&fg->relay.lock);
    pthread_cond_destroy(&fg->relay.cond);
    free(fg->images);
    free(fg->ready);
    free(fg->timing_total_us);
    free(fg->timing_own_us);
    free(fg);
}

/* ------------------------------------------------------------ present */

static VkResult submit_real(gfg_gpu_fg *fg, ring_slot *rs, const VkPresentInfoKHR *app,
                            uint32_t idx, uint64_t v) {
    VkSemaphore waits[17];
    VkPipelineStageFlags stages[17];
    uint64_t wait_values[17];
    uint32_t nw = 0;
    if (app->waitSemaphoreCount > 16) return VK_ERROR_OUT_OF_HOST_MEMORY;
    for (uint32_t i = 0; i < app->waitSemaphoreCount; ++i) {
        waits[nw] = app->pWaitSemaphores[i];
        stages[nw] = VK_PIPELINE_STAGE_TRANSFER_BIT;
        wait_values[nw++] = 0; /* binary: ignored */
    }
    if (fg->last_te_value) {
        /* all TE work submitted so far (it reads the slot we overwrite) */
        waits[nw] = fg->timeline;
        stages[nw] = VK_PIPELINE_STAGE_TRANSFER_BIT;
        wait_values[nw++] = fg->last_te_value;
    }
    VkSemaphore signals[2] = {fg->timeline, fg->ready[idx]};
    uint64_t signal_values[2] = {v, 0};
    VkTimelineSemaphoreSubmitInfo tsi = {.sType = VK_STRUCTURE_TYPE_TIMELINE_SEMAPHORE_SUBMIT_INFO,
        .waitSemaphoreValueCount = nw, .pWaitSemaphoreValues = wait_values,
        .signalSemaphoreValueCount = 2, .pSignalSemaphoreValues = signal_values};
    VkSubmitInfo si = {.sType = VK_STRUCTURE_TYPE_SUBMIT_INFO, .pNext = &tsi,
        .waitSemaphoreCount = nw, .pWaitSemaphores = waits, .pWaitDstStageMask = stages,
        .commandBufferCount = 1, .pCommandBuffers = &rs->real_cb,
        .signalSemaphoreCount = 2, .pSignalSemaphores = signals};
    return fg->QueueSubmit(fg->queue, 1, &si, VK_NULL_HANDLE);
}

/* acquire + copy + present one synthetic output; 1 presented, 0 skipped, -1 error */
static int present_synthetic(gfg_gpu_fg *fg, ring_slot *rs, int k, uint64_t v,
                             PFN_vkQueuePresentKHR next, double *next_us) {
    uint32_t img = UINT32_MAX;
    double tp = now_us();
    VkResult r = fg->AcquireNextImageKHR(fg->device, fg->swapchain, 0, rs->acquire_sem[k],
                                         VK_NULL_HANDLE, &img);
    fg->phase_us[2] += now_us() - tp;
    tp = now_us();
    if (r == VK_NOT_READY || r == VK_TIMEOUT) { STAT_ADD(acquire_not_ready, 1); return 0; }
    if ((r != VK_SUCCESS && r != VK_SUBOPTIMAL_KHR) || img >= fg->image_count) {
        if (r == VK_SUCCESS || r == VK_SUBOPTIMAL_KHR) {
            /* impossible index: acquire semaphore is pending, never reuse it */
            fg->disabled = 1;
        }
        return -1;
    }
    /* From here the acquire semaphore is signalled: it MUST be waited. */
    int recorded = record_generated(fg, rs->gen_cb[k], fg->dst[k].image, fg->images[img]);
    const uint64_t value = v + 1 + (uint64_t)k;
    VkSemaphore waits[2] = {rs->acquire_sem[k], fg->timeline};
    VkPipelineStageFlags stages[2] = {VK_PIPELINE_STAGE_TRANSFER_BIT, VK_PIPELINE_STAGE_TRANSFER_BIT};
    uint64_t wait_values[2] = {0, value};
    VkTimelineSemaphoreSubmitInfo tsi = {.sType = VK_STRUCTURE_TYPE_TIMELINE_SEMAPHORE_SUBMIT_INFO,
        .waitSemaphoreValueCount = 2, .pWaitSemaphoreValues = wait_values};
    VkSubmitInfo si = {.sType = VK_STRUCTURE_TYPE_SUBMIT_INFO, .pNext = &tsi,
        .waitSemaphoreCount = 2, .pWaitSemaphores = waits, .pWaitDstStageMask = stages,
        .commandBufferCount = recorded ? 1u : 0u, .pCommandBuffers = &rs->gen_cb[k],
        .signalSemaphoreCount = 1, .pSignalSemaphores = &fg->ready[img]};
    /* Even if recording failed we still submit the semaphore hop so the
     * acquired image is returned (presented with undefined content is worse
     * than an error, so a failed record disables the bridge after this). */
    r = fg->QueueSubmit(fg->queue, 1, &si, VK_NULL_HANDLE);
    fg->phase_us[3] += now_us() - tp;
    if (!ok(r)) { fail_log(fg, "synthetic submit", r); fg->disabled = 1; return -1; }
    if (!recorded) fg->disabled = 1;
    VkPresentInfoKHR pi = {.sType = VK_STRUCTURE_TYPE_PRESENT_INFO_KHR,
        .waitSemaphoreCount = 1, .pWaitSemaphores = &fg->ready[img],
        .swapchainCount = 1, .pSwapchains = &fg->swapchain, .pImageIndices = &img};
    const double t = now_us();
    r = next(fg->queue, &pi);
    *next_us += now_us() - t;
    if (r != VK_SUCCESS && r != VK_SUBOPTIMAL_KHR) {
        fail_log(fg, "synthetic present", r);
        return -1;
    }
    STAT_ADD(synthetic_presents, 1);
    return 1;
}

VkResult gfg_gpu_fg_present(gfg_gpu_fg *fg, VkQueue queue, const VkPresentInfoKHR *app,
                            PFN_vkQueuePresentKHR next) {
    if (!fg || !app || !next) return VK_ERROR_INITIALIZATION_FAILED;
    const double t0 = now_us();
    double next_us = 0.0;
    STAT_ADD(real_presents, 1);
    const uint64_t frame = fg->frame++;
    const uint32_t idx = app->pImageIndices[0];
    VkResult result;
    if (fg->disabled || queue != fg->queue || idx >= fg->image_count ||
        app->waitSemaphoreCount > 16) {
        fg->te_gap = 1;
        if (frame) STAT_ADD(skipped_synthetic, 2);
        const double t = now_us();
        result = next(queue, app);
        next_us += now_us() - t;
        goto timing;
    }
    fg->in_present = 1;
    if (fg->verify) verify_collect(fg, 0);
    ring_slot *rs = &fg->ring[frame % fg->ring_size];
    int pass_through = 0;
    /* test-only: alternate the two skip paths on every inject_every-th frame */
    const int inject = fg->inject_every && frame % fg->inject_every == fg->inject_every - 1;
    const int inject_te_busy = inject && (frame / fg->inject_every) % 2 == 0;
    if (inject && !inject_te_busy) { STAT_ADD(ring_busy, 1); pass_through = 1; }
    if (!pass_through && rs->busy) {
        VkResult fs = fg->GetFenceStatus(fg->device, rs->fence);
        if (fs == VK_SUCCESS) rs->busy = 0;
        else if (fs == VK_NOT_READY) { STAT_ADD(ring_busy, 1); pass_through = 1; }
        else { fg->disabled = 1; pass_through = 1; }
    }
    if (!pass_through && !fg->shared_sync && !relay_has_room(fg)) {
        STAT_ADD(te_busy, 1);
        pass_through = 1;
    }
    if (!pass_through && !ok(fg->ResetFences(fg->device, 1, &rs->fence))) {
        fg->disabled = 1;
        pass_through = 1;
    }
    if (!pass_through && !record_real(fg, rs->real_cb, fg->images[idx], fg->src[fg->te_slot].image,
                                     fg->verify ? fg->verify_hist[fg->te_slot] : VK_NULL_HANDLE)) {
        fg->disabled = 1;
        pass_through = 1;
    }
    if (pass_through) {
        /* app semaphores untouched: forward unmodified */
        fg->te_gap = 1;
        if (frame) STAT_ADD(skipped_synthetic, 2);
        fg->in_present = 0;
        const double t = now_us();
        result = next(queue, app);
        next_us += now_us() - t;
        goto timing;
    }
    const uint64_t v = fg->next_value;
    double tp = now_us();
    VkResult r = submit_real(fg, rs, app, idx, v);
    fg->phase_us[0] += now_us() - tp;
    if (!ok(r)) {
        /* A failed vkQueueSubmit may have consumed the app's waits; never
         * replay them. Report it like the driver would. */
        fail_log(fg, "real submit", r);
        STAT_ADD(errors, 1);
        fg->disabled = 1;
        fg->in_present = 0;
        result = r;
        goto timing;
    }
    fg->next_value += 3;
    /* From here ready[idx] is signalled: the real present below waits it. */
    te_submit s = {0};
    s.slot = fg->te_slot;
    s.count = 2;
    s.timestamps[0] = 1.0f / 3.0f;
    s.timestamps[1] = 2.0f / 3.0f;
    s.wait_value = v;
    s.signal_first = v + 1;
    s.nonblocking = 1;
    s.discontinuity = fg->te_frames > 0 && fg->te_gap;
    s.lmc_tier = fg->lmc_tier;
    const int generate = fg->te_frames > 0 && !fg->te_gap;
    tp = now_us();
    VkResult tr = inject_te_busy ? VK_NOT_READY : te_submit_frame(fg->context, &s);
    fg->phase_us[1] += now_us() - tp;
    int presented = 0;
    if (tr == VK_SUCCESS) {
        fg->last_te_value = v + 2;
        if (!fg->shared_sync) relay_push(fg, v);
        fg->te_slot ^= 1u;
        fg->te_frames++;
        fg->te_gap = 0;
        if (!generate) STAT_ADD(holds, 1);
        if (generate) {
            for (int k = 0; k < 2; ++k) {
                int g = present_synthetic(fg, rs, k, v, next, &next_us);
                if (g <= 0) {
                    if (g < 0) STAT_ADD(errors, 1);
                    break;
                }
                ++presented;
            }
            if (fg->verify && presented == 2 && frame % fg->verify_every == 0)
                verify_submit(fg, v, fg->te_slot ^ 1u);
        }
    } else {
        if (tr == VK_NOT_READY) STAT_ADD(te_busy, 1);
        else {
            fprintf(stderr, "[gfg-native] gpu-bridge te_submit: %s (%d)\n", te_last_error(), (int)tr);
            STAT_ADD(errors, 1);
            fg->disabled = 1;
        }
        fg->te_gap = 1;
    }
    if (frame) STAT_ADD(skipped_synthetic, (uint64_t)(2 - presented));
    /* the ring slot's fence covers everything submitted for this frame */
    tp = now_us();
    if (ok(fg->QueueSubmit(fg->queue, 0, NULL, rs->fence))) rs->busy = 1;
    else fg->disabled = 1;
    fg->phase_us[4] += now_us() - tp;
    fg->phase_n++;
    fg->in_present = 0;
    {
        VkPresentInfoKHR real = *app; /* pNext (present id, fences, ...) untouched */
        real.waitSemaphoreCount = 1;
        real.pWaitSemaphores = &fg->ready[idx];
        const double t = now_us();
        result = next(queue, &real);
        next_us += now_us() - t;
    }
    if (fg->log && (frame < 4 || frame % 120 == 0))
        fprintf(stderr, "[gfg-native] gpu-bridge frame=%llu te=%d generated=%d presented=%d\n",
                (unsigned long long)frame, (int)tr, generate, presented);
timing:
    if (fg->timing_total_us && fg->timing_count < TIMING_CAP) {
        const double total = now_us() - t0;
        fg->timing_total_us[fg->timing_count] = total;
        fg->timing_own_us[fg->timing_count] = total - next_us;
        fg->timing_count++;
    }
    return result;
}
