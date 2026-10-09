/* GFG Frame OS — gfg-pacer Vulkan layer glue (VK_LAYER_GFG_pacer).
 *
 * Implicit layer.  Hooks the frame boundaries and hands the timing questions to the
 * Presentation Scheduler:
 *
 *   vkAcquireNextImageKHR  frame start: gfg_sched_frame_start(now), sleep the answer, forward;
 *                          the return time is the frame start of (swapchain, image)
 *   vkQueuePresentKHR      frame ready (= now): gfg_sched_present(ready), sleep until the
 *                          release time, forward, publish telemetry once it returned (the
 *                          layers below, e.g. a frame generator, may hold it)
 *   vkCreateSwapchainKHR   counted (recreations are a stutter/resize signal), forwarded
 *
 * Modes (control channel): act = the above; shadow = scheduler runs, no sleeps; observe = no
 * scheduler, measurements only.  All three publish the same telemetry (metrics.h).
 *
 * Frame start per (swapchain, image index), not per device: DXVK / vkd3d acquire on their
 * presenter thread, several images ahead of the present that uses them.
 *
 * Everything else is forwarded untouched.  The layer acts only while the control channel says
 * enabled (see control.h); otherwise every hook is a plain forward.  Any internal error switches
 * the whole process to pass-through for good.
 *
 * Dispatch: one record per VkInstance / VkDevice keyed by the loader dispatch key (the first
 * pointer of a dispatchable handle; a VkQueue shares its VkDevice's key, a VkPhysicalDevice its
 * VkInstance's).  One mutex per device guards its scheduler; sleeps happen outside it.
 *
 * Engine name: kept per instance and copied to each device at vkCreateDevice.  Telemetry carries
 * the engine of the device that publishes (the presenting one): a process can hold several
 * instances, e.g. a frame-generation layer's own internal instance ("mako-engine") next to the
 * game's (DXVK).  A device that never created a swapchain can never own the telemetry.
 */
#define _GNU_SOURCE
#include <errno.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include <vulkan/vk_layer.h>
#include <vulkan/vulkan.h>

#include "control.h"
#include "metrics.h"
#include "scheduler.h"

#define LAYER_EXPORT __attribute__((visibility("default")))
#define NS_PER_MS 1000000ll
#define MAX_SLEEP_NS 1000000000ll   /* a request beyond this is a broken clock: internal error */
#define ACQ_SWAPCHAINS 8
#define ACQ_IMAGES 8

typedef struct inst_data {
    struct inst_data *next;
    void *key;
    PFN_vkGetInstanceProcAddr gipa;
    PFN_vkDestroyInstance destroy_instance;
    char engine[GFG_CTL_ENGINE_LEN];   /* VkApplicationInfo.pEngineName, NUL-padded */
} inst_data;

typedef struct dev_data {
    struct dev_data *next;
    void *key;
    VkDevice device;
    PFN_vkGetDeviceProcAddr gdpa;
    PFN_vkDestroyDevice destroy_device;
    PFN_vkAcquireNextImageKHR acquire;
    PFN_vkAcquireNextImage2KHR acquire2;
    PFN_vkQueuePresentKHR present;
    PFN_vkCreateSwapchainKHR create_swapchain;
    char engine[GFG_CTL_ENGINE_LEN];   /* of the instance the device was created from */
    pthread_mutex_t lock;          /* guards everything below */
    int enabled;                   /* layer enabled at the last hook: metrics belong to this period */
    int sched_active;              /* scheduler initialised (act/shadow) */
    uint64_t serial;               /* control-channel state serial applied */
    uint32_t mode;
    uint32_t generation;           /* Governor's policy generation in effect */
    int64_t shadow_delay_ns;       /* shadow: start delay act would have applied to this frame */
    struct {
        VkSwapchainKHR swapchain;
        int64_t acquired_ns[ACQ_IMAGES];   /* acquire return per image index; 0 = none */
    } acq[ACQ_SWAPCHAINS];
    int acq_next;                  /* round-robin eviction */
    uint32_t swapchains_created;
    gfg_sched sched;
    gfg_metrics metrics;
} dev_data;

/* A mutex, not a rwlock: pthread_rwlock_* are GLIBC_2.34 symbols when built on a new glibc. */
static pthread_mutex_t g_map_lock = PTHREAD_MUTEX_INITIALIZER;
static inst_data *g_instances;
static dev_data *g_devices;
static int g_passthrough;          /* sticky; atomic access */
static int g_debug = -1;
/* The one (device, swapchain) of this process that publishes; another takes over after
 * GFG_CTL_TAKEOVER_NS without a present from it. */
static pthread_mutex_t g_owner_lock = PTHREAD_MUTEX_INITIALIZER;
static const dev_data *g_owner_dev;
static VkSwapchainKHR g_owner_sc;
static int64_t g_owner_ns;

static void *dispatch_key(const void *handle)
{
    return *(void *const *)handle;
}

static int debug_on(void)
{
    if (__atomic_load_n(&g_debug, __ATOMIC_RELAXED) < 0) {
        const char *v = getenv("GFG_FRAME_OS_DEBUG");
        __atomic_store_n(&g_debug, (v && *v == '1') ? 1 : 0, __ATOMIC_RELAXED);
    }
    return __atomic_load_n(&g_debug, __ATOMIC_RELAXED);
}

static int passthrough(void)
{
    return __atomic_load_n(&g_passthrough, __ATOMIC_ACQUIRE);
}

static int64_t now_ns(void)
{
    struct timespec ts;
    if (clock_gettime(CLOCK_MONOTONIC, &ts) != 0)
        return -1;
    return (int64_t)ts.tv_sec * 1000000000ll + ts.tv_nsec;
}

static void fail(const char *why)
{
    if (!__atomic_exchange_n(&g_passthrough, 1, __ATOMIC_ACQ_REL)) {
        fprintf(stderr, "[gfg-pacer] internal error (%s): pass-through for this process\n", why);
        gfg_ctl_mark_passthrough(now_ns());
    }
}

static void sleep_until(int64_t t_ns)
{
    struct timespec ts = { .tv_sec = t_ns / 1000000000ll, .tv_nsec = t_ns % 1000000000ll };
    int r;
    while ((r = clock_nanosleep(CLOCK_MONOTONIC, TIMER_ABSTIME, &ts, NULL)) == EINTR)
        ;
    if (r != 0)
        fail("clock_nanosleep");
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

/* ---- scheduler glue ---- */

/* Bring d to the control-channel state st (d->lock held).  Returns 0 when the layer is disabled
 * (forward only), else 1 with d->mode set. */
static int sync_policy_locked(dev_data *d, const gfg_ctl_state *st)
{
    if (!st->enabled) {
        d->enabled = 0;          /* re-enable starts from a fresh timeline and fresh metrics */
        d->sched_active = 0;
        return 0;
    }
    if (!d->enabled) {
        gfg_metrics_reset(&d->metrics);
        d->enabled = 1;
    }
    if (st->mode == GFG_MODE_OBSERVE) {
        d->sched_active = 0;
    } else if (!d->sched_active) {
        gfg_sched_init(&d->sched, &st->policy);
        d->sched_active = 1;
        d->shadow_delay_ns = 0;
    } else if (d->serial != st->serial) {
        gfg_sched_set_policy(&d->sched, &st->policy);   /* shadow -> act keeps what was learned */
    }
    d->serial = st->serial;
    d->mode = st->mode;
    d->generation = st->generation;
    return 1;
}

static void frame_start(dev_data *d)
{
    gfg_ctl_state st;
    int64_t now, delay = 0, cap;
    int sleep_it = 0;
    if (passthrough())
        return;
    if ((now = now_ns()) < 0 || gfg_ctl_poll(now, &st) != 0) {
        fail("clock/control");
        return;
    }
    if (pthread_mutex_lock(&d->lock) != 0) {
        fail("mutex");
        return;
    }
    if (sync_policy_locked(d, &st)) {
        if (d->sched_active)
            delay = gfg_sched_frame_start(&d->sched, now);
        cap = (int64_t)(d->sched.policy.max_wait_ms * NS_PER_MS) + NS_PER_MS;
        if (delay < 0 || delay > cap) {
            pthread_mutex_unlock(&d->lock);
            fail("frame_start delay out of range");
            return;
        }
        sleep_it = d->mode == GFG_MODE_ACT;
        /* shadow: the frame really starts now; remember what act would have added */
        d->shadow_delay_ns = d->mode == GFG_MODE_SHADOW ? delay : 0;
    }
    pthread_mutex_unlock(&d->lock);
    if (sleep_it && delay > 0)
        sleep_until(now + delay);
}

/* After an acquire forward that started at before_ns returned image idx (d->lock not held). */
static void acquired(dev_data *d, VkSwapchainKHR sc, uint32_t idx, int64_t before_ns)
{
    int64_t now;
    int i;
    if (passthrough())
        return;
    if ((now = now_ns()) < 0) {
        fail("clock");
        return;
    }
    if (pthread_mutex_lock(&d->lock) != 0) {
        fail("mutex");
        return;
    }
    if (d->enabled)
        gfg_metrics_acquired(&d->metrics, now - before_ns);
    if (idx < ACQ_IMAGES) {
        for (i = 0; i < ACQ_SWAPCHAINS && d->acq[i].swapchain != sc; i++)
            ;
        if (i == ACQ_SWAPCHAINS) {
            i = d->acq_next;
            d->acq_next = (d->acq_next + 1) % ACQ_SWAPCHAINS;
            memset(&d->acq[i], 0, sizeof(d->acq[i]));
            d->acq[i].swapchain = sc;
        }
        d->acq[i].acquired_ns[idx] = now;
    }
    pthread_mutex_unlock(&d->lock);
}

/* Frame start of the first presented image the layer saw acquired; consumes the entries
 * (d->lock held).  0 when unknown. */
static int64_t take_frame_start_locked(dev_data *d, const VkPresentInfoKHR *info)
{
    int64_t start = 0;
    for (uint32_t k = 0; k < info->swapchainCount; k++) {
        uint32_t idx = info->pImageIndices[k];
        if (idx >= ACQ_IMAGES)
            continue;
        for (int i = 0; i < ACQ_SWAPCHAINS; i++)
            if (d->acq[i].swapchain == info->pSwapchains[k]) {
                if (!start)
                    start = d->acq[i].acquired_ns[idx];
                d->acq[i].acquired_ns[idx] = 0;
                break;
            }
    }
    return start;
}

/* Before forwarding a present.  Returns 1 when present_done must run after forwarding, with
 * *fwd_ns = the forward time. */
static int present_gate(dev_data *d, const VkPresentInfoKHR *info, int64_t *fwd_ns)
{
    gfg_ctl_state st;
    int64_t ready, release, wait = 0, start;
    if (passthrough())
        return 0;
    if ((ready = now_ns()) < 0 || gfg_ctl_poll(ready, &st) != 0) {
        fail("clock/control");
        return 0;
    }
    if (pthread_mutex_lock(&d->lock) != 0) {
        fail("mutex");
        return 0;
    }
    start = take_frame_start_locked(d, info);
    if (!sync_policy_locked(d, &st)) {
        pthread_mutex_unlock(&d->lock);
        return 0;
    }
    gfg_metrics_frame_start(&d->metrics, start);
    gfg_metrics_ready(&d->metrics, ready);
    if (d->mode == GFG_MODE_ACT) {
        if (start > 0)
            d->sched.frame_start_ns = start;
        release = gfg_sched_present(&d->sched, ready);
        wait = release - ready;
        if (wait < 0 || wait > MAX_SLEEP_NS) {
            pthread_mutex_unlock(&d->lock);
            fail("present release out of range");
            return 0;
        }
        /* Hold at most one real-frame slot: a later release only happens when the frame beat
         * its cost estimate after a capped start delay; the next slot absorbs the difference. */
        if (wait > d->sched.period_ns)
            wait = d->sched.period_ns;
    } else if (d->mode == GFG_MODE_SHADOW) {
        /* Replay the frame on act's timeline: same cost, started shadow_delay later. */
        if (start > 0)
            d->sched.frame_start_ns = start + d->shadow_delay_ns;
        release = gfg_sched_present(&d->sched, ready + d->shadow_delay_ns);
        if (release < ready + d->shadow_delay_ns) {
            pthread_mutex_unlock(&d->lock);
            fail("present release out of range");
            return 0;
        }
        d->shadow_delay_ns = 0;
    }
    pthread_mutex_unlock(&d->lock);

    if (wait > 0)
        sleep_until(ready + wait);
    if ((*fwd_ns = now_ns()) < 0) {
        fail("clock");
        return 0;
    }
    return 1;
}

/* This (device, swapchain) publishes for the process.  Only a device that created a swapchain
 * can own: a helper instance's device (no swapchain) never takes over. */
static int owns_telemetry(const dev_data *d, VkSwapchainKHR sc, int64_t now)
{
    int mine;
    if (!sc || !__atomic_load_n(&d->swapchains_created, __ATOMIC_RELAXED))
        return 0;
    pthread_mutex_lock(&g_owner_lock);
    mine = (g_owner_dev == d && g_owner_sc == sc) || now - g_owner_ns > GFG_CTL_TAKEOVER_NS;
    if (mine) {
        g_owner_dev = d;
        g_owner_sc = sc;
        g_owner_ns = now;
    }
    pthread_mutex_unlock(&g_owner_lock);
    return mine;
}

/* The present forwarded at fwd returned: finish the frame, publish telemetry. */
static void present_done(dev_data *d, const VkPresentInfoKHR *info, int64_t fwd)
{
    gfg_ctl_telemetry t;
    int64_t ret;
    if ((ret = now_ns()) < 0) {
        fail("clock");
        return;
    }
    if (pthread_mutex_lock(&d->lock) != 0) {
        fail("mutex");
        return;
    }
    gfg_metrics *m = &d->metrics;
    if (!d->enabled) {                 /* disabled by another thread meanwhile */
        pthread_mutex_unlock(&d->lock);
        return;
    }
    gfg_metrics_released(m, fwd, ret);
    if (!owns_telemetry(d, info->pSwapchains[0], ret)) {
        pthread_mutex_unlock(&d->lock);
        return;
    }
    memset(&t, 0, sizeof(t));
    t.reserved = GFG_SUPPORT_TICK_SHAPING | GFG_SUPPORT_STALL_SHIELD;
    t.frames = m->frames;
    t.cost_p50_ms = gfg_ring_quantile(&m->costs_ms, 0.5);
    t.cost_q_ms = gfg_ring_quantile(&m->costs_ms, d->sched_active ? d->sched.policy.cost_quantile : 0.95);
    t.freshness_ms = m->freshness_ms;
    t.present_interval_p50_ms = gfg_ring_quantile(&m->intervals_ms, 0.5);
    t.present_interval_p95_ms = gfg_ring_quantile(&m->intervals_ms, 0.95);
    t.last_present_ns = fwd;
    t.last_present_return_ns = ret;
    t.present_hold_ms = m->present_hold_ms;
    t.acquire_block_ms = m->acquire_block_ms;
    t.applied_generation = d->generation;
    uint32_t sc = __atomic_load_n(&d->swapchains_created, __ATOMIC_RELAXED);
    t.swapchain_recreations = sc > 1 ? sc - 1 : 0;
    if (d->sched_active) {
        const gfg_stats *s = gfg_sched_stats(&d->sched);
        t.hits = s->hits;
        t.misses = s->misses;
        t.margin_ms = s->margin_ms;
        t.avg_delay_ms = s->avg_delay_ms;
        if (d->mode == GFG_MODE_ACT) {
            if (d->sched.policy.tick_shaping)
                t.reserved |= GFG_ACTIVE_TICK_SHAPING;
            if (d->sched.policy.pacing && d->sched.policy.stall_shield)
                t.reserved |= GFG_ACTIVE_STALL_SHIELD;
        }
    }
    memcpy(t.engine, d->engine, sizeof(t.engine));   /* the publishing device's own instance */
    pthread_mutex_unlock(&d->lock);
    gfg_ctl_publish(&t);
}

/* ---- hooks ---- */

static VKAPI_ATTR VkResult VKAPI_CALL layer_AcquireNextImageKHR(VkDevice device, VkSwapchainKHR swapchain,
                                                                 uint64_t timeout, VkSemaphore semaphore,
                                                                 VkFence fence, uint32_t *pImageIndex)
{
    dev_data *d = find_device(dispatch_key(device));
    if (!d || !d->acquire)
        return VK_ERROR_INITIALIZATION_FAILED;
    frame_start(d);
    int64_t before = now_ns();
    VkResult r = d->acquire(device, swapchain, timeout, semaphore, fence, pImageIndex);
    if (r == VK_SUCCESS || r == VK_SUBOPTIMAL_KHR)
        acquired(d, swapchain, *pImageIndex, before);
    return r;
}

static VKAPI_ATTR VkResult VKAPI_CALL layer_AcquireNextImage2KHR(VkDevice device,
                                                                  const VkAcquireNextImageInfoKHR *info,
                                                                  uint32_t *pImageIndex)
{
    dev_data *d = find_device(dispatch_key(device));
    if (!d || !d->acquire2)
        return VK_ERROR_INITIALIZATION_FAILED;
    frame_start(d);
    int64_t before = now_ns();
    VkResult r = d->acquire2(device, info, pImageIndex);
    if (r == VK_SUCCESS || r == VK_SUBOPTIMAL_KHR)
        acquired(d, info->swapchain, *pImageIndex, before);
    return r;
}

static VKAPI_ATTR VkResult VKAPI_CALL layer_QueuePresentKHR(VkQueue queue, const VkPresentInfoKHR *info)
{
    dev_data *d = find_device(dispatch_key(queue));
    int64_t fwd = 0;
    if (!d || !d->present)
        return VK_ERROR_INITIALIZATION_FAILED;
    int gated = info && info->swapchainCount > 0 && present_gate(d, info, &fwd);
    VkResult r = d->present(queue, info);
    if (gated)
        present_done(d, info, fwd);
    return r;
}

static VKAPI_ATTR VkResult VKAPI_CALL layer_CreateSwapchainKHR(VkDevice device, const VkSwapchainCreateInfoKHR *ci,
                                                                const VkAllocationCallbacks *alloc,
                                                                VkSwapchainKHR *out)
{
    dev_data *d = find_device(dispatch_key(device));
    if (!d || !d->create_swapchain)
        return VK_ERROR_INITIALIZATION_FAILED;
    VkResult r = d->create_swapchain(device, ci, alloc, out);
    if (r == VK_SUCCESS)
        __atomic_add_fetch(&d->swapchains_created, 1, __ATOMIC_RELAXED);
    return r;
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
    i->gipa = gipa;
    i->destroy_instance = destroy;
    if (ci->pApplicationInfo && ci->pApplicationInfo->pEngineName)
        strncpy(i->engine, ci->pApplicationInfo->pEngineName, sizeof(i->engine) - 1);
    pthread_mutex_lock(&g_map_lock);
    i->next = g_instances;
    g_instances = i;
    pthread_mutex_unlock(&g_map_lock);
    if (debug_on())
        fprintf(stderr, "[gfg-pacer] instance created (engine '%s')\n", i->engine);
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
    pthread_mutex_unlock(&g_map_lock);
    if (!i)
        return;
    i->destroy_instance(instance, alloc);
    free(i);
}

static VKAPI_ATTR VkResult VKAPI_CALL layer_CreateDevice(VkPhysicalDevice phys, const VkDeviceCreateInfo *ci,
                                                          const VkAllocationCallbacks *alloc, VkDevice *out)
{
    VkLayerDeviceCreateInfo *link = (VkLayerDeviceCreateInfo *)ci->pNext;
    while (link && !(link->sType == VK_STRUCTURE_TYPE_LOADER_DEVICE_CREATE_INFO && link->function == VK_LAYER_LINK_INFO))
        link = (VkLayerDeviceCreateInfo *)link->pNext;
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
    d->gdpa = gdpa;
    d->destroy_device = destroy;
    /* NULL when VK_KHR_swapchain is not enabled: then the hooks are not exposed either */
    d->acquire = (PFN_vkAcquireNextImageKHR)gdpa(*out, "vkAcquireNextImageKHR");
    d->acquire2 = (PFN_vkAcquireNextImage2KHR)gdpa(*out, "vkAcquireNextImage2KHR");
    d->present = (PFN_vkQueuePresentKHR)gdpa(*out, "vkQueuePresentKHR");
    d->create_swapchain = (PFN_vkCreateSwapchainKHR)gdpa(*out, "vkCreateSwapchainKHR");
    pthread_mutex_lock(&g_map_lock);
    /* a physical device shares its instance's dispatch key */
    for (inst_data *i = g_instances; i; i = i->next)
        if (i->key == dispatch_key(phys)) {
            memcpy(d->engine, i->engine, sizeof(d->engine));
            break;
        }
    d->next = g_devices;
    g_devices = d;
    pthread_mutex_unlock(&g_map_lock);
    if (debug_on())
        fprintf(stderr, "[gfg-pacer] device created (swapchain hooks: %s) engine '%s'\n", d->present ? "yes" : "no",
                d->engine);
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
    pthread_mutex_lock(&g_owner_lock);   /* a later device at the same address must not inherit */
    if (g_owner_dev == d) {
        g_owner_dev = NULL;
        g_owner_sc = VK_NULL_HANDLE;
        g_owner_ns = 0;
    }
    pthread_mutex_unlock(&g_owner_lock);
    d->destroy_device(device, alloc);
    pthread_mutex_destroy(&d->lock);
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
    if (d->acquire) HOOK(AcquireNextImageKHR);
    if (d->acquire2) HOOK(AcquireNextImage2KHR);
    if (d->present) HOOK(QueuePresentKHR);
    if (d->create_swapchain) HOOK(CreateSwapchainKHR);
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
