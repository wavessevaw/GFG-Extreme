/* GFG HUD — Vulkan layer glue (VK_LAYER_GFG_hud).
 *
 * Implicit-capable layer, listed in VK_INSTANCE_LAYERS after the frame-generation layer (so it
 * sits below it and sees every presented frame, real and generated).  It stamps a small
 * pre-rendered overlay bitmap (overlay.h) into each presented swapchain image with copies only:
 * no shaders, no blending, no render passes.
 *
 *   vkCreateSwapchainKHR   writes "<w> <h> <hud>\n" to the extent file; adds TRANSFER_DST to the image
 *                          usage when the surface supports it (else the swapchain is no-HUD);
 *                          records format / extent / images
 *   vkQueuePresentKHR      for each HUD swapchain in the present: per image a reusable command
 *                          buffer (PRESENT_SRC -> TRANSFER_DST, one vkCmdCopyBufferToImage region
 *                          per overlay row run, -> PRESENT_SRC), one submit on the present queue
 *                          waiting on the app's semaphores (TRANSFER stage) and signalling one
 *                          layer semaphore per image; the present then waits on those only
 *   vkGetDeviceQueue(2)    queue -> family (command pool per (device, family))
 *   vkDestroySwapchainKHR / vkDestroyDevice: wait for the layer's fences, free its objects
 *
 * Overlay pixels are converted once per overlay change into a per-swapchain host-visible,
 * coherent staging buffer (no rewrite while a copy from it may still run: all image fences are
 * waited first).  Each image's command buffer is re-recorded only when that conversion changed
 * and only after its fence signalled.
 *
 * Failure policy: anything that goes wrong for a swapchain turns that swapchain into plain
 * pass-through for the rest of its life.  The app's present is always forwarded, and with the
 * app's own semaphores whenever the layer's submit did not happen.
 *
 * Dispatch: one record per VkInstance / VkDevice keyed by the loader dispatch key (as gfg-pacer).
 * One mutex per device guards its swapchains, slots, pools and queue map.
 */
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include <vulkan/vk_layer.h>
#include <vulkan/vulkan.h>

#include "overlay.h"

#define LAYER_EXPORT __attribute__((visibility("default")))
#define FENCE_WAIT_NS 100000000ull      /* per present: an image's previous HUD copy (normally long done) */
#define DESTROY_WAIT_NS 5000000000ull   /* teardown: then leak rather than free in-use objects */
#define MAX_QUEUES 64
#define MAX_POOLS 16
#define MAX_PRESENT 16                   /* swapchains per present that can carry a HUD */
#define MAX_WAITS 32

_Static_assert(GFG_HUD_VK_R8G8B8A8_UNORM == VK_FORMAT_R8G8B8A8_UNORM, "format number");
_Static_assert(GFG_HUD_VK_R8G8B8A8_SRGB == VK_FORMAT_R8G8B8A8_SRGB, "format number");
_Static_assert(GFG_HUD_VK_B8G8R8A8_UNORM == VK_FORMAT_B8G8R8A8_UNORM, "format number");
_Static_assert(GFG_HUD_VK_B8G8R8A8_SRGB == VK_FORMAT_B8G8R8A8_SRGB, "format number");
_Static_assert(GFG_HUD_VK_A2R10G10B10_UNORM_PACK32 == VK_FORMAT_A2R10G10B10_UNORM_PACK32, "format number");
_Static_assert(GFG_HUD_VK_A2B10G10R10_UNORM_PACK32 == VK_FORMAT_A2B10G10R10_UNORM_PACK32, "format number");

/* Next-layer device functions.  HUD: needed to draw; SWAPCHAIN: VK_KHR_swapchain. */
#define HUD_FUNCS(X) \
    X(CreateCommandPool) X(DestroyCommandPool) X(AllocateCommandBuffers) X(FreeCommandBuffers) \
    X(BeginCommandBuffer) X(EndCommandBuffer) X(CmdPipelineBarrier) X(CmdCopyBufferToImage) \
    X(QueueSubmit) X(QueueWaitIdle) X(CreateFence) X(DestroyFence) X(WaitForFences) X(ResetFences) \
    X(CreateSemaphore) X(DestroySemaphore) X(CreateBuffer) X(DestroyBuffer) \
    X(GetBufferMemoryRequirements) X(AllocateMemory) X(FreeMemory) X(BindBufferMemory) X(MapMemory) \
    X(UnmapMemory) X(GetSwapchainImagesKHR)
#define OTHER_FUNCS(X) \
    X(DestroyDevice) X(GetDeviceQueue) X(GetDeviceQueue2) X(CreateSwapchainKHR) X(DestroySwapchainKHR) \
    X(QueuePresentKHR)

typedef struct inst_data {
    struct inst_data *next;
    void *key;
    VkInstance instance;
    PFN_vkGetInstanceProcAddr gipa;
    PFN_vkDestroyInstance destroy_instance;
} inst_data;

typedef struct hud_slot {          /* per swapchain image */
    VkCommandBuffer cmd;
    uint32_t family;               /* pool cmd came from */
    VkFence fence;                 /* signalled when the last submit of cmd finished */
    VkSemaphore sem;               /* signalled by the HUD submit, waited by the present */
    int submitted;                 /* fence pending (not yet waited + reset) */
    uint64_t recorded;             /* sc->build recorded into cmd; 0 = none */
} hud_slot;

typedef struct hud_swapchain {
    struct hud_swapchain *next;
    VkSwapchainKHR handle;
    int hud;                       /* 0: pass-through for the rest of its life */
    gfg_hud_kind kind;
    VkExtent2D extent;
    uint32_t image_count;
    VkImage *images;
    hud_slot *slots;
    VkBuffer buf;                  /* staging: converted overlay */
    VkDeviceMemory mem;
    uint8_t *map;
    VkDeviceSize cap;
    int have_gen;
    uint64_t ov_gen;               /* source generation converted */
    uint64_t build;                /* bumped per conversion (slots re-record) */
    gfg_hud_region *rows;
    VkBufferImageCopy *regions;
    uint32_t nregions, region_cap;
    uint64_t hud_frames;
} hud_swapchain;

typedef struct dev_data {
    struct dev_data *next;
    void *key;
    VkDevice device;
    VkPhysicalDevice phys;
    PFN_vkGetDeviceProcAddr gdpa;
    PFN_vkSetDeviceLoaderData set_loader_data;
    PFN_vkGetPhysicalDeviceSurfaceCapabilitiesKHR surface_caps;
#define X(fn) PFN_vk##fn fn;
    HUD_FUNCS(X)
    OTHER_FUNCS(X)
#undef X
    int hud_ok;                    /* everything needed to draw was resolved */
    VkPhysicalDeviceMemoryProperties mem_props;
    VkQueueFamilyProperties *families;
    uint32_t nfamilies;
    pthread_mutex_t lock;          /* guards everything below */
    struct { VkQueue queue; uint32_t family; } queues[MAX_QUEUES];
    uint32_t nqueues;
    struct { uint32_t family; VkCommandPool pool; } pools[MAX_POOLS];
    uint32_t npools;
    hud_swapchain *swapchains;
} dev_data;

static pthread_mutex_t g_map_lock = PTHREAD_MUTEX_INITIALIZER;
static inst_data *g_instances;
static dev_data *g_devices;
static int g_debug = -1;
static int g_source_ready;         /* under g_map_lock (pthread_once is a GLIBC_2.34 symbol) */
static gfg_hud_source g_source;

static void *dispatch_key(const void *handle)
{
    return *(void *const *)handle;
}

static int debug_on(void)
{
    if (__atomic_load_n(&g_debug, __ATOMIC_RELAXED) < 0) {
        const char *v = getenv("GFG_HUD_DEBUG");
        __atomic_store_n(&g_debug, (v && *v == '1') ? 1 : 0, __ATOMIC_RELAXED);
    }
    return __atomic_load_n(&g_debug, __ATOMIC_RELAXED);
}

static int64_t now_ns(void)
{
    struct timespec ts;
    if (clock_gettime(CLOCK_MONOTONIC, &ts) != 0)
        return 0;
    return (int64_t)ts.tv_sec * 1000000000ll + ts.tv_nsec;
}

static gfg_hud_source *source(void)
{
    pthread_mutex_lock(&g_map_lock);
    if (!g_source_ready) {
        gfg_hud_source_init(&g_source, getenv("GFG_HUD_FILE"));
        g_source_ready = 1;
    }
    pthread_mutex_unlock(&g_map_lock);
    return &g_source;
}

/* ---- dispatch maps ---- */

static inst_data *find_instance(void *key)
{
    inst_data *i;
    pthread_mutex_lock(&g_map_lock);
    for (i = g_instances; i && i->key != key; i = i->next)
        ;
    pthread_mutex_unlock(&g_map_lock);
    return i;
}

static dev_data *find_device(void *key)
{
    dev_data *d;
    pthread_mutex_lock(&g_map_lock);
    for (d = g_devices; d && d->key != key; d = d->next)
        ;
    pthread_mutex_unlock(&g_map_lock);
    return d;
}

/* ---- per-device helpers (d->lock held) ---- */

static int queue_family(const dev_data *d, VkQueue q, uint32_t *family)
{
    for (uint32_t i = 0; i < d->nqueues; i++)
        if (d->queues[i].queue == q) {
            *family = d->queues[i].family;
            return 1;
        }
    return 0;
}

static void remember_queue(dev_data *d, VkQueue q, uint32_t family)
{
    uint32_t f;
    if (!q || queue_family(d, q, &f) || d->nqueues == MAX_QUEUES)
        return;
    d->queues[d->nqueues].queue = q;
    d->queues[d->nqueues].family = family;
    d->nqueues++;
}

/* Copies into images need a family with transfer and 1x1x1 image transfer granularity. */
static int family_can_copy(const dev_data *d, uint32_t family)
{
    if (family >= d->nfamilies)
        return 0;
    const VkQueueFamilyProperties *p = &d->families[family];
    if (p->queueFlags & (VK_QUEUE_GRAPHICS_BIT | VK_QUEUE_COMPUTE_BIT))
        return 1;   /* granularity (1,1,1) guaranteed */
    return (p->queueFlags & VK_QUEUE_TRANSFER_BIT) && p->minImageTransferGranularity.width == 1 &&
           p->minImageTransferGranularity.height == 1 && p->minImageTransferGranularity.depth == 1;
}

static VkCommandPool get_pool(dev_data *d, uint32_t family)
{
    VkCommandPool pool = VK_NULL_HANDLE;
    for (uint32_t i = 0; i < d->npools; i++)
        if (d->pools[i].family == family)
            return d->pools[i].pool;
    if (d->npools == MAX_POOLS)
        return VK_NULL_HANDLE;
    VkCommandPoolCreateInfo ci = { .sType = VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO,
                                   .flags = VK_COMMAND_POOL_CREATE_RESET_COMMAND_BUFFER_BIT,
                                   .queueFamilyIndex = family };
    if (d->CreateCommandPool(d->device, &ci, NULL, &pool) != VK_SUCCESS)
        return VK_NULL_HANDLE;
    d->pools[d->npools].family = family;
    d->pools[d->npools].pool = pool;
    d->npools++;
    return pool;
}

static void sc_fail(hud_swapchain *sc, const char *why, VkResult r)
{
    if (!sc->hud)
        return;
    sc->hud = 0;
    fprintf(stderr, "[gfg-hud] swapchain 0x%llx: %s (VkResult %d): HUD off for this swapchain\n",
            (unsigned long long)(uintptr_t)sc->handle, why, (int)r);
}

/* Wait for a slot's pending submit and reset its fence.  VK_TIMEOUT: still running. */
static VkResult slot_wait(dev_data *d, hud_slot *s, uint64_t timeout)
{
    VkResult r;
    if (!s->submitted)
        return VK_SUCCESS;
    r = d->WaitForFences(d->device, 1, &s->fence, VK_TRUE, timeout);
    if (r != VK_SUCCESS)
        return r;
    if ((r = d->ResetFences(d->device, 1, &s->fence)) != VK_SUCCESS)
        return r;
    s->submitted = 0;
    return VK_SUCCESS;
}

static VkResult sc_wait_all(dev_data *d, hud_swapchain *sc, uint64_t timeout)
{
    for (uint32_t i = 0; i < sc->image_count; i++) {
        VkResult r = slot_wait(d, &sc->slots[i], timeout);
        if (r != VK_SUCCESS)
            return r;
    }
    return VK_SUCCESS;
}

static void free_staging(dev_data *d, hud_swapchain *sc)
{
    if (sc->map)
        d->UnmapMemory(d->device, sc->mem);
    if (sc->buf)
        d->DestroyBuffer(d->device, sc->buf, NULL);
    if (sc->mem)
        d->FreeMemory(d->device, sc->mem, NULL);
    sc->map = NULL;
    sc->buf = VK_NULL_HANDLE;
    sc->mem = VK_NULL_HANDLE;
    sc->cap = 0;
}

/* Free everything the layer made for sc and sc itself.  idle: no submit of it can still run
 * (otherwise its Vulkan objects are leaked rather than destroyed while in use). */
static void sc_free(dev_data *d, hud_swapchain *sc, int idle)
{
    if (idle && d->hud_ok) {
        for (uint32_t i = 0; sc->slots && i < sc->image_count; i++) {
            hud_slot *s = &sc->slots[i];
            if (s->cmd) {
                for (uint32_t p = 0; p < d->npools; p++)
                    if (d->pools[p].family == s->family)
                        d->FreeCommandBuffers(d->device, d->pools[p].pool, 1, &s->cmd);
            }
            if (s->fence)
                d->DestroyFence(d->device, s->fence, NULL);
            if (s->sem)
                d->DestroySemaphore(d->device, s->sem, NULL);
        }
        free_staging(d, sc);
    }
    if (debug_on())
        fprintf(stderr, "[gfg-hud] swapchain 0x%llx released (hud frames %llu)\n",
                (unsigned long long)(uintptr_t)sc->handle, (unsigned long long)sc->hud_frames);
    free(sc->slots);
    free(sc->images);
    free(sc->rows);
    free(sc->regions);
    free(sc);
}

static int memory_type(const dev_data *d, uint32_t bits, VkMemoryPropertyFlags want)
{
    for (uint32_t i = 0; i < d->mem_props.memoryTypeCount && i < 32; i++)
        if ((bits & (1u << i)) && (d->mem_props.memoryTypes[i].propertyFlags & want) == want)
            return (int)i;
    return -1;
}

static VkResult ensure_staging(dev_data *d, hud_swapchain *sc, VkDeviceSize size)
{
    VkResult r;
    VkMemoryRequirements req;
    void *map = NULL;
    if (sc->buf && sc->cap >= size)
        return VK_SUCCESS;
    free_staging(d, sc);
    VkBufferCreateInfo bci = { .sType = VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO, .size = size,
                               .usage = VK_BUFFER_USAGE_TRANSFER_SRC_BIT, .sharingMode = VK_SHARING_MODE_EXCLUSIVE };
    if ((r = d->CreateBuffer(d->device, &bci, NULL, &sc->buf)) != VK_SUCCESS) {
        sc->buf = VK_NULL_HANDLE;
        return r;
    }
    d->GetBufferMemoryRequirements(d->device, sc->buf, &req);
    int type = memory_type(d, req.memoryTypeBits, VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT);
    if (type < 0)
        return VK_ERROR_FEATURE_NOT_PRESENT;
    VkMemoryAllocateInfo mai = { .sType = VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO, .allocationSize = req.size,
                                 .memoryTypeIndex = (uint32_t)type };
    if ((r = d->AllocateMemory(d->device, &mai, NULL, &sc->mem)) != VK_SUCCESS) {
        sc->mem = VK_NULL_HANDLE;
        return r;
    }
    if ((r = d->BindBufferMemory(d->device, sc->buf, sc->mem, 0)) != VK_SUCCESS)
        return r;
    if ((r = d->MapMemory(d->device, sc->mem, 0, VK_WHOLE_SIZE, 0, &map)) != VK_SUCCESS || !map)
        return r != VK_SUCCESS ? r : VK_ERROR_MEMORY_MAP_FAILED;
    sc->map = map;
    sc->cap = size;
    return VK_SUCCESS;
}

/* Bring sc's staging buffer and regions to source generation gen.  VK_TIMEOUT: a previous copy
 * still runs, keep the old conversion this frame. */
static VkResult sc_update(dev_data *d, hud_swapchain *sc, uint64_t gen)
{
    gfg_hud_source *src = source();
    VkResult r = VK_SUCCESS;
    uint32_t x, y, n = 0;
    if (sc->have_gen && sc->ov_gen == gen)
        return VK_SUCCESS;
    if ((r = sc_wait_all(d, sc, FENCE_WAIT_NS)) != VK_SUCCESS)
        return r;
    pthread_mutex_lock(&src->lock);
    const gfg_hud_header *h = &src->hdr;
    if (src->valid && gfg_hud_place(sc->extent.width, sc->extent.height, h->width, h->height, h->corner, h->margin,
                                    &x, &y) == 0) {
        if (h->height > sc->region_cap) {
            gfg_hud_region *rows = realloc(sc->rows, h->height * sizeof(*rows));
            if (rows)
                sc->rows = rows;
            VkBufferImageCopy *regions = realloc(sc->regions, h->height * sizeof(*regions));
            if (regions)
                sc->regions = regions;
            if (!rows || !regions)
                r = VK_ERROR_OUT_OF_HOST_MEMORY;
            else
                sc->region_cap = h->height;
        }
        if (r == VK_SUCCESS)
            r = ensure_staging(d, sc, gfg_hud_pixel_bytes(h));
        if (r == VK_SUCCESS)
            n = gfg_hud_build(h, src->pixels, sc->kind, sc->extent.width, sc->extent.height, sc->map, sc->rows);
    }
    pthread_mutex_unlock(&src->lock);
    if (r != VK_SUCCESS)
        return r;
    for (uint32_t i = 0; i < n; i++) {
        VkBufferImageCopy c = {
            .bufferOffset = sc->rows[i].buf_offset,
            .imageSubresource = { VK_IMAGE_ASPECT_COLOR_BIT, 0, 0, 1 },
            .imageOffset = { (int32_t)sc->rows[i].x, (int32_t)sc->rows[i].y, 0 },
            .imageExtent = { sc->rows[i].len, 1, 1 },
        };
        sc->regions[i] = c;
    }
    sc->nregions = n;
    sc->ov_gen = gen;
    sc->have_gen = 1;
    sc->build++;
    if (debug_on())
        fprintf(stderr, "[gfg-hud] swapchain 0x%llx overlay gen %llu: %u row regions\n",
                (unsigned long long)(uintptr_t)sc->handle, (unsigned long long)gen, n);
    return VK_SUCCESS;
}

/* Make slot s usable on a queue of family: previous submit done, objects exist.  VK_TIMEOUT:
 * skip the HUD this frame. */
static VkResult slot_ready(dev_data *d, hud_slot *s, uint32_t family)
{
    VkResult r;
    VkCommandPool pool;
    if ((r = slot_wait(d, s, FENCE_WAIT_NS)) != VK_SUCCESS)
        return r;
    if (!s->fence) {
        VkFenceCreateInfo fci = { .sType = VK_STRUCTURE_TYPE_FENCE_CREATE_INFO };
        if ((r = d->CreateFence(d->device, &fci, NULL, &s->fence)) != VK_SUCCESS) {
            s->fence = VK_NULL_HANDLE;
            return r;
        }
    }
    if (!s->sem) {
        VkSemaphoreCreateInfo sci = { .sType = VK_STRUCTURE_TYPE_SEMAPHORE_CREATE_INFO };
        if ((r = d->CreateSemaphore(d->device, &sci, NULL, &s->sem)) != VK_SUCCESS) {
            s->sem = VK_NULL_HANDLE;
            return r;
        }
    }
    if (s->cmd && s->family != family) {   /* presented from another queue family now */
        for (uint32_t p = 0; p < d->npools; p++)
            if (d->pools[p].family == s->family)
                d->FreeCommandBuffers(d->device, d->pools[p].pool, 1, &s->cmd);
        s->cmd = NULL;
    }
    if (!s->cmd) {
        if (!(pool = get_pool(d, family)))
            return VK_ERROR_INITIALIZATION_FAILED;
        VkCommandBufferAllocateInfo ai = { .sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO, .commandPool = pool,
                                           .level = VK_COMMAND_BUFFER_LEVEL_PRIMARY, .commandBufferCount = 1 };
        if ((r = d->AllocateCommandBuffers(d->device, &ai, &s->cmd)) != VK_SUCCESS) {
            s->cmd = NULL;
            return r;
        }
        /* a layer-made dispatchable handle needs the loader's dispatch pointer */
        if ((r = d->set_loader_data(d->device, s->cmd)) != VK_SUCCESS) {
            d->FreeCommandBuffers(d->device, pool, 1, &s->cmd);
            s->cmd = NULL;
            return r;
        }
        s->family = family;
        s->recorded = 0;
    }
    return VK_SUCCESS;
}

static VkResult record(dev_data *d, hud_swapchain *sc, uint32_t idx, hud_slot *s)
{
    VkResult r;
    VkCommandBufferBeginInfo bi = { .sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO };
    VkImageMemoryBarrier b = {
        .sType = VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER,
        .srcAccessMask = 0,
        .dstAccessMask = VK_ACCESS_TRANSFER_WRITE_BIT,
        .oldLayout = VK_IMAGE_LAYOUT_PRESENT_SRC_KHR,
        .newLayout = VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL,
        .srcQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED,
        .dstQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED,
        .image = sc->images[idx],
        .subresourceRange = { VK_IMAGE_ASPECT_COLOR_BIT, 0, 1, 0, VK_REMAINING_ARRAY_LAYERS },
    };
    s->recorded = 0;
    if ((r = d->BeginCommandBuffer(s->cmd, &bi)) != VK_SUCCESS)   /* implicit reset (pool flag) */
        return r;
    /* first scope: the app's semaphore waits at TRANSFER (dependency chain) */
    d->CmdPipelineBarrier(s->cmd, VK_PIPELINE_STAGE_TRANSFER_BIT, VK_PIPELINE_STAGE_TRANSFER_BIT, 0, 0, NULL, 0, NULL,
                          1, &b);
    d->CmdCopyBufferToImage(s->cmd, sc->buf, sc->images[idx], VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL, sc->nregions,
                            sc->regions);
    b.srcAccessMask = VK_ACCESS_TRANSFER_WRITE_BIT;
    b.dstAccessMask = 0;
    b.oldLayout = VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL;
    b.newLayout = VK_IMAGE_LAYOUT_PRESENT_SRC_KHR;
    /* the signal semaphore's first scope covers the rest */
    d->CmdPipelineBarrier(s->cmd, VK_PIPELINE_STAGE_TRANSFER_BIT, VK_PIPELINE_STAGE_BOTTOM_OF_PIPE_BIT, 0, 0, NULL, 0,
                          NULL, 1, &b);
    if ((r = d->EndCommandBuffer(s->cmd)) != VK_SUCCESS)
        return r;
    s->recorded = sc->build;
    return VK_SUCCESS;
}

static hud_swapchain *find_swapchain(dev_data *d, VkSwapchainKHR h)
{
    hud_swapchain *sc;
    for (sc = d->swapchains; sc && sc->handle != h; sc = sc->next)
        ;
    return sc;
}

/* ---- hooks ---- */

static VKAPI_ATTR VkResult VKAPI_CALL layer_QueuePresentKHR(VkQueue queue, const VkPresentInfoKHR *info)
{
    dev_data *d = find_device(dispatch_key(queue));
    VkSemaphore sems[MAX_PRESENT];
    VkCommandBuffer cmds[MAX_PRESENT];
    hud_slot *slots[MAX_PRESENT];
    hud_swapchain *scs[MAX_PRESENT];
    VkPipelineStageFlags stages[MAX_WAITS];
    uint32_t n = 0, family;
    VkResult r;
    if (!d || !d->QueuePresentKHR)
        return VK_ERROR_INITIALIZATION_FAILED;
    if (!d->hud_ok || !info || !info->swapchainCount || info->waitSemaphoreCount > MAX_WAITS)
        return d->QueuePresentKHR(queue, info);
    pthread_mutex_lock(&d->lock);
    if (!d->swapchains || !queue_family(d, queue, &family) || !family_can_copy(d, family)) {
        pthread_mutex_unlock(&d->lock);
        return d->QueuePresentKHR(queue, info);
    }
    uint64_t gen = gfg_hud_source_poll(source(), now_ns());
    for (uint32_t k = 0; k < info->swapchainCount && n < MAX_PRESENT; k++) {
        hud_swapchain *sc = find_swapchain(d, info->pSwapchains[k]);
        uint32_t idx = info->pImageIndices[k];
        if (!sc || !sc->hud || idx >= sc->image_count)
            continue;
        if ((r = sc_update(d, sc, gen)) != VK_SUCCESS) {
            if (r != VK_TIMEOUT)
                sc_fail(sc, "overlay conversion", r);
            continue;
        }
        if (!sc->nregions)
            continue;
        hud_slot *s = &sc->slots[idx];
        if ((r = slot_ready(d, s, family)) != VK_SUCCESS) {
            if (r != VK_TIMEOUT)
                sc_fail(sc, "command buffer / sync objects", r);
            continue;
        }
        if (s->recorded != sc->build && (r = record(d, sc, idx, s)) != VK_SUCCESS) {
            sc_fail(sc, "recording", r);
            continue;
        }
        sems[n] = s->sem;
        cmds[n] = s->cmd;
        slots[n] = s;
        scs[n] = sc;
        n++;
    }
    if (!n) {
        pthread_mutex_unlock(&d->lock);
        return d->QueuePresentKHR(queue, info);
    }
    for (uint32_t i = 0; i < info->waitSemaphoreCount; i++)
        stages[i] = VK_PIPELINE_STAGE_TRANSFER_BIT;
    VkSubmitInfo si = { .sType = VK_STRUCTURE_TYPE_SUBMIT_INFO, .waitSemaphoreCount = info->waitSemaphoreCount,
                        .pWaitSemaphores = info->pWaitSemaphores, .pWaitDstStageMask = stages,
                        .commandBufferCount = n, .pCommandBuffers = cmds, .signalSemaphoreCount = n,
                        .pSignalSemaphores = sems };
    if ((r = d->QueueSubmit(queue, 1, &si, slots[0]->fence)) != VK_SUCCESS) {
        /* a failed submit leaves the app's semaphores untouched: present them as they were */
        for (uint32_t i = 0; i < n; i++)
            sc_fail(scs[i], "submit", r);
        pthread_mutex_unlock(&d->lock);
        return d->QueuePresentKHR(queue, info);
    }
    slots[0]->submitted = 1;
    scs[0]->hud_frames++;
    /* One submit carries every image; each further image's fence rides an empty submit right
     * behind it (signals once all earlier work on the queue finished). */
    for (uint32_t i = 1; i < n; i++) {
        if ((r = d->QueueSubmit(queue, 0, NULL, slots[i]->fence)) == VK_SUCCESS) {
            slots[i]->submitted = 1;
        } else {
            d->QueueWaitIdle(queue);   /* the copy is done; its fence just never signals */
            sc_fail(scs[i], "fence submit", r);
        }
        scs[i]->hud_frames++;
    }
    pthread_mutex_unlock(&d->lock);
    VkPresentInfoKHR pi = *info;
    pi.waitSemaphoreCount = n;
    pi.pWaitSemaphores = sems;
    return d->QueuePresentKHR(queue, &pi);
}

static void write_extent(uint32_t w, uint32_t h, int hud)
{
    const char *p = getenv("GFG_HUD_EXTENT_FILE");
    p = p && *p ? p : GFG_HUD_DEFAULT_EXTENT;
    if (gfg_hud_write_extent(p, w, h, hud) != 0 && debug_on())
        fprintf(stderr, "[gfg-hud] cannot write extent file %s\n", p);
}

/* New HUD record for a created swapchain; NULL = pass-through. */
static hud_swapchain *sc_new(dev_data *d, VkSwapchainKHR handle, const VkSwapchainCreateInfoKHR *ci, gfg_hud_kind kind)
{
    uint32_t count = 0;
    hud_swapchain *sc = calloc(1, sizeof(*sc));
    if (!sc)
        return NULL;
    sc->handle = handle;
    sc->kind = kind;
    sc->extent = ci->imageExtent;
    if (d->GetSwapchainImagesKHR(d->device, handle, &count, NULL) != VK_SUCCESS || !count ||
        !(sc->images = calloc(count, sizeof(VkImage))) || !(sc->slots = calloc(count, sizeof(hud_slot)))) {
        sc_free(d, sc, 1);
        return NULL;
    }
    VkResult r = d->GetSwapchainImagesKHR(d->device, handle, &count, sc->images);
    if (r != VK_SUCCESS && r != VK_INCOMPLETE) {
        sc_free(d, sc, 1);
        return NULL;
    }
    sc->image_count = count;
    sc->hud = 1;
    return sc;
}

static VKAPI_ATTR VkResult VKAPI_CALL layer_CreateSwapchainKHR(VkDevice device, const VkSwapchainCreateInfoKHR *ci,
                                                                const VkAllocationCallbacks *alloc,
                                                                VkSwapchainKHR *out)
{
    dev_data *d = find_device(dispatch_key(device));
    VkSwapchainCreateInfoKHR mod;
    VkSurfaceCapabilitiesKHR caps;
    const char *why = NULL;
    if (!d || !d->CreateSwapchainKHR)
        return VK_ERROR_INITIALIZATION_FAILED;
    if (!ci)
        return d->CreateSwapchainKHR(device, ci, alloc, out);
    gfg_hud_kind kind = gfg_hud_kind_for_format((uint32_t)ci->imageFormat);
    if (!d->hud_ok)
        why = "device functions missing";
    else if (!kind)
        why = "image format";
    else if (ci->imageColorSpace != VK_COLOR_SPACE_SRGB_NONLINEAR_KHR)
        why = "colour space";   /* sRGB pixels into an HDR (PQ / linear) image would be wrong */
    else if (ci->flags & VK_SWAPCHAIN_CREATE_PROTECTED_BIT_KHR)
        why = "protected swapchain";
    else if (!(ci->imageUsage & VK_IMAGE_USAGE_TRANSFER_DST_BIT) &&
             (!d->surface_caps || d->surface_caps(d->phys, ci->surface, &caps) != VK_SUCCESS ||
              !(caps.supportedUsageFlags & VK_IMAGE_USAGE_TRANSFER_DST_BIT)))
        why = "surface lacks TRANSFER_DST usage";
    mod = *ci;
    if (!why)
        mod.imageUsage |= VK_IMAGE_USAGE_TRANSFER_DST_BIT;
    VkResult r = d->CreateSwapchainKHR(device, &mod, alloc, out);
    if (r != VK_SUCCESS && mod.imageUsage != ci->imageUsage) {
        why = "creation with TRANSFER_DST failed";
        r = d->CreateSwapchainKHR(device, ci, alloc, out);   /* exactly what the app asked for */
    }
    if (r != VK_SUCCESS)
        return r;
    if (!why) {
        hud_swapchain *sc = sc_new(d, *out, ci, kind);
        if (sc) {
            pthread_mutex_lock(&d->lock);
            sc->next = d->swapchains;
            d->swapchains = sc;
            pthread_mutex_unlock(&d->lock);
        } else {
            why = "swapchain images";
        }
    }
    write_extent(ci->imageExtent.width, ci->imageExtent.height, !why);
    if (debug_on())
        fprintf(stderr, "[gfg-hud] swapchain 0x%llx %ux%u format %d: hud %s%s\n", (unsigned long long)(uintptr_t)*out,
                ci->imageExtent.width, ci->imageExtent.height, (int)ci->imageFormat, why ? "no: " : "yes",
                why ? why : "");
    return r;
}

static VKAPI_ATTR void VKAPI_CALL layer_DestroySwapchainKHR(VkDevice device, VkSwapchainKHR swapchain,
                                                             const VkAllocationCallbacks *alloc)
{
    dev_data *d = find_device(dispatch_key(device));
    hud_swapchain **pp, *sc = NULL;
    if (!d || !d->DestroySwapchainKHR)
        return;
    pthread_mutex_lock(&d->lock);
    for (pp = &d->swapchains; swapchain && *pp; pp = &(*pp)->next)
        if ((*pp)->handle == swapchain) {
            sc = *pp;
            *pp = sc->next;
            break;
        }
    /* our copies touch its images: done before the swapchain goes */
    int idle = !sc || !d->hud_ok || sc_wait_all(d, sc, DESTROY_WAIT_NS) == VK_SUCCESS;
    d->DestroySwapchainKHR(device, swapchain, alloc);
    if (sc)
        sc_free(d, sc, idle);
    pthread_mutex_unlock(&d->lock);
}

static VKAPI_ATTR void VKAPI_CALL layer_GetDeviceQueue(VkDevice device, uint32_t family, uint32_t index, VkQueue *q)
{
    dev_data *d = find_device(dispatch_key(device));
    if (!d || !d->GetDeviceQueue)
        return;
    d->GetDeviceQueue(device, family, index, q);
    pthread_mutex_lock(&d->lock);
    remember_queue(d, *q, family);
    pthread_mutex_unlock(&d->lock);
}

static VKAPI_ATTR void VKAPI_CALL layer_GetDeviceQueue2(VkDevice device, const VkDeviceQueueInfo2 *info, VkQueue *q)
{
    dev_data *d = find_device(dispatch_key(device));
    if (!d || !d->GetDeviceQueue2)
        return;
    d->GetDeviceQueue2(device, info, q);
    pthread_mutex_lock(&d->lock);
    remember_queue(d, *q, info->queueFamilyIndex);
    pthread_mutex_unlock(&d->lock);
}

/* ---- instance / device lifetime ---- */

static VKAPI_ATTR PFN_vkVoidFunction VKAPI_CALL layer_GetInstanceProcAddr(VkInstance instance, const char *name);
static VKAPI_ATTR PFN_vkVoidFunction VKAPI_CALL layer_GetDeviceProcAddr(VkDevice device, const char *name);

static VKAPI_ATTR VkResult VKAPI_CALL layer_CreateInstance(const VkInstanceCreateInfo *ci,
                                                            const VkAllocationCallbacks *alloc, VkInstance *out)
{
    VkLayerInstanceCreateInfo *link = (VkLayerInstanceCreateInfo *)ci->pNext;
    while (link && !(link->sType == VK_STRUCTURE_TYPE_LOADER_INSTANCE_CREATE_INFO && link->function == VK_LAYER_LINK_INFO))
        link = (VkLayerInstanceCreateInfo *)link->pNext;
    if (!link || !link->u.pLayerInfo)
        return VK_ERROR_INITIALIZATION_FAILED;
    PFN_vkGetInstanceProcAddr gipa = link->u.pLayerInfo->pfnNextGetInstanceProcAddr;
    link->u.pLayerInfo = link->u.pLayerInfo->pNext;   /* advance the chain for the next layer */
    PFN_vkCreateInstance create = (PFN_vkCreateInstance)gipa(VK_NULL_HANDLE, "vkCreateInstance");
    if (!create)
        return VK_ERROR_INITIALIZATION_FAILED;
    VkResult r = create(ci, alloc, out);
    if (r != VK_SUCCESS)
        return r;
    inst_data *i = calloc(1, sizeof(*i));
    PFN_vkDestroyInstance destroy = (PFN_vkDestroyInstance)gipa(*out, "vkDestroyInstance");
    if (!i || !destroy) {
        free(i);
        if (destroy)
            destroy(*out, alloc);
        return VK_ERROR_INITIALIZATION_FAILED;
    }
    i->key = dispatch_key(*out);
    i->instance = *out;
    i->gipa = gipa;
    i->destroy_instance = destroy;
    pthread_mutex_lock(&g_map_lock);
    i->next = g_instances;
    g_instances = i;
    pthread_mutex_unlock(&g_map_lock);
    return VK_SUCCESS;
}

static VKAPI_ATTR void VKAPI_CALL layer_DestroyInstance(VkInstance instance, const VkAllocationCallbacks *alloc)
{
    inst_data **pp, *i = NULL;
    if (!instance)
        return;
    pthread_mutex_lock(&g_map_lock);
    for (pp = &g_instances; *pp; pp = &(*pp)->next)
        if ((*pp)->key == dispatch_key(instance)) {
            i = *pp;
            *pp = i->next;
            break;
        }
    if (!g_instances && !g_devices && g_source_ready) {   /* last one out: the loader may unload us */
        gfg_hud_source_free(&g_source);
        g_source_ready = 0;
    }
    pthread_mutex_unlock(&g_map_lock);
    if (!i)
        return;
    i->destroy_instance(instance, alloc);
    free(i);
}

/* Instance-level facts the HUD needs (memory types, queue families, surface usage). */
static void device_physical_info(dev_data *d, VkPhysicalDevice phys)
{
    PFN_vkGetPhysicalDeviceMemoryProperties mem_props = NULL;
    PFN_vkGetPhysicalDeviceQueueFamilyProperties qf = NULL;
    inst_data *i = find_instance(dispatch_key(phys));   /* a physical device shares its instance's key */
    if (!i)
        return;
    mem_props = (PFN_vkGetPhysicalDeviceMemoryProperties)i->gipa(i->instance, "vkGetPhysicalDeviceMemoryProperties");
    qf = (PFN_vkGetPhysicalDeviceQueueFamilyProperties)i->gipa(i->instance, "vkGetPhysicalDeviceQueueFamilyProperties");
    d->surface_caps = (PFN_vkGetPhysicalDeviceSurfaceCapabilitiesKHR)i->gipa(
        i->instance, "vkGetPhysicalDeviceSurfaceCapabilitiesKHR");
    if (!mem_props || !qf)
        return;
    mem_props(phys, &d->mem_props);
    uint32_t n = 0;
    qf(phys, &n, NULL);
    if (n && (d->families = calloc(n, sizeof(*d->families)))) {
        qf(phys, &n, d->families);
        d->nfamilies = n;
    }
}

static VKAPI_ATTR VkResult VKAPI_CALL layer_CreateDevice(VkPhysicalDevice phys, const VkDeviceCreateInfo *ci,
                                                          const VkAllocationCallbacks *alloc, VkDevice *out)
{
    VkLayerDeviceCreateInfo *link = (VkLayerDeviceCreateInfo *)ci->pNext, *cb = (VkLayerDeviceCreateInfo *)ci->pNext;
    while (link && !(link->sType == VK_STRUCTURE_TYPE_LOADER_DEVICE_CREATE_INFO && link->function == VK_LAYER_LINK_INFO))
        link = (VkLayerDeviceCreateInfo *)link->pNext;
    while (cb && !(cb->sType == VK_STRUCTURE_TYPE_LOADER_DEVICE_CREATE_INFO && cb->function == VK_LOADER_DATA_CALLBACK))
        cb = (VkLayerDeviceCreateInfo *)cb->pNext;
    if (!link || !link->u.pLayerInfo)
        return VK_ERROR_INITIALIZATION_FAILED;
    PFN_vkGetInstanceProcAddr gipa = link->u.pLayerInfo->pfnNextGetInstanceProcAddr;
    PFN_vkGetDeviceProcAddr gdpa = link->u.pLayerInfo->pfnNextGetDeviceProcAddr;
    link->u.pLayerInfo = link->u.pLayerInfo->pNext;
    PFN_vkCreateDevice create = (PFN_vkCreateDevice)gipa(VK_NULL_HANDLE, "vkCreateDevice");
    if (!create)
        return VK_ERROR_INITIALIZATION_FAILED;
    VkResult r = create(phys, ci, alloc, out);
    if (r != VK_SUCCESS)
        return r;
    dev_data *d = calloc(1, sizeof(*d));
    PFN_vkDestroyDevice destroy = (PFN_vkDestroyDevice)gdpa(*out, "vkDestroyDevice");
    if (!d || !destroy || pthread_mutex_init(&d->lock, NULL) != 0) {
        free(d);
        if (destroy)
            destroy(*out, alloc);
        return VK_ERROR_INITIALIZATION_FAILED;
    }
    d->key = dispatch_key(*out);
    d->device = *out;
    d->phys = phys;
    d->gdpa = gdpa;
    d->set_loader_data = cb ? cb->u.pfnSetDeviceLoaderData : NULL;
    /* swapchain entry points are NULL when VK_KHR_swapchain is not enabled: then not hooked */
#define X(fn) d->fn = (PFN_vk##fn)gdpa(*out, "vk" #fn);
    HUD_FUNCS(X)
    OTHER_FUNCS(X)
#undef X
    device_physical_info(d, phys);
    d->hud_ok = d->set_loader_data && d->nfamilies && d->QueuePresentKHR && d->CreateSwapchainKHR &&
                d->DestroySwapchainKHR;
#define X(fn) d->hud_ok = d->hud_ok && d->fn;
    HUD_FUNCS(X)
#undef X
    pthread_mutex_lock(&g_map_lock);
    d->next = g_devices;
    g_devices = d;
    pthread_mutex_unlock(&g_map_lock);
    if (debug_on())
        fprintf(stderr, "[gfg-hud] device created (swapchain hooks: %s, hud: %s)\n", d->QueuePresentKHR ? "yes" : "no",
                d->hud_ok ? "yes" : "no");
    return VK_SUCCESS;
}

static VKAPI_ATTR void VKAPI_CALL layer_DestroyDevice(VkDevice device, const VkAllocationCallbacks *alloc)
{
    dev_data **pp, *d = NULL;
    if (!device)
        return;
    pthread_mutex_lock(&g_map_lock);
    for (pp = &g_devices; *pp; pp = &(*pp)->next)
        if ((*pp)->key == dispatch_key(device)) {
            d = *pp;
            *pp = d->next;
            break;
        }
    pthread_mutex_unlock(&g_map_lock);
    if (!d)
        return;
    pthread_mutex_lock(&d->lock);
    while (d->swapchains) {   /* swapchains the app leaked: our part of them goes now */
        hud_swapchain *sc = d->swapchains;
        d->swapchains = sc->next;
        sc_free(d, sc, d->hud_ok && sc_wait_all(d, sc, DESTROY_WAIT_NS) == VK_SUCCESS);
    }
    for (uint32_t i = 0; i < d->npools; i++)
        d->DestroyCommandPool(device, d->pools[i].pool, NULL);
    pthread_mutex_unlock(&d->lock);
    d->DestroyDevice(device, alloc);
    pthread_mutex_destroy(&d->lock);
    free(d->families);
    free(d);
}

/* ---- proc addr ---- */

#define HOOK(fn) if (!strcmp(name, "vk" #fn)) return (PFN_vkVoidFunction)layer_##fn

static VKAPI_ATTR PFN_vkVoidFunction VKAPI_CALL layer_GetDeviceProcAddr(VkDevice device, const char *name)
{
    HOOK(GetDeviceProcAddr);
    HOOK(DestroyDevice);
    if (!device)
        return NULL;
    dev_data *d = find_device(dispatch_key(device));
    if (!d)
        return NULL;
    if (d->GetDeviceQueue) HOOK(GetDeviceQueue);
    if (d->GetDeviceQueue2) HOOK(GetDeviceQueue2);
    if (d->QueuePresentKHR) HOOK(QueuePresentKHR);
    if (d->CreateSwapchainKHR) HOOK(CreateSwapchainKHR);
    if (d->DestroySwapchainKHR) HOOK(DestroySwapchainKHR);
    return d->gdpa(device, name);
}

static VKAPI_ATTR PFN_vkVoidFunction VKAPI_CALL layer_GetInstanceProcAddr(VkInstance instance, const char *name)
{
    HOOK(GetInstanceProcAddr);
    HOOK(CreateInstance);
    HOOK(DestroyInstance);
    HOOK(CreateDevice);
    HOOK(GetDeviceProcAddr);
    if (!instance)
        return NULL;
    inst_data *i = find_instance(dispatch_key(instance));
    return i ? i->gipa(instance, name) : NULL;
}

#undef HOOK

/* Exported entry points: thin wrappers, so in-layer references never bind to the loader's
 * identically named global symbols. */
LAYER_EXPORT VKAPI_ATTR PFN_vkVoidFunction VKAPI_CALL vkGetInstanceProcAddr(VkInstance instance, const char *name)
{
    return layer_GetInstanceProcAddr(instance, name);
}

LAYER_EXPORT VKAPI_ATTR PFN_vkVoidFunction VKAPI_CALL vkGetDeviceProcAddr(VkDevice device, const char *name)
{
    return layer_GetDeviceProcAddr(device, name);
}

LAYER_EXPORT VKAPI_ATTR VkResult VKAPI_CALL vkNegotiateLoaderLayerInterfaceVersion(VkNegotiateLayerInterface *v)
{
    if (!v || v->sType != LAYER_NEGOTIATE_INTERFACE_STRUCT || v->loaderLayerInterfaceVersion < 2)
        return VK_ERROR_INITIALIZATION_FAILED;
    v->loaderLayerInterfaceVersion = 2;
    v->pfnGetInstanceProcAddr = layer_GetInstanceProcAddr;
    v->pfnGetDeviceProcAddr = layer_GetDeviceProcAddr;
    v->pfnGetPhysicalDeviceProcAddr = NULL;
    return VK_SUCCESS;
}
