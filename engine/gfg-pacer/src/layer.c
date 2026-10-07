/* GFG Frame OS — gfg-pacer Vulkan layer glue (VK_LAYER_GFG_pacer).
 *
 * Implicit layer.  Hooks two calls and hands the timing questions to the Presentation Scheduler:
 *
 *   vkAcquireNextImageKHR  frame start: gfg_sched_frame_start(now), sleep the answer, forward
 *   vkQueuePresentKHR      frame ready (= now): gfg_sched_present(ready), sleep until the
 *                          release time, forward, publish telemetry
 *
 * Everything else is forwarded untouched.  The layer acts only while the control channel says
 * enabled (see control.h); otherwise every hook is a plain forward.  Any internal error switches
 * the whole process to pass-through for good.
 *
 * Dispatch: one record per VkInstance / VkDevice keyed by the loader dispatch key (the first
 * pointer of a dispatchable handle; a VkQueue shares its VkDevice's key).  One mutex per device
 * guards its scheduler; sleeps happen outside it.
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
#include "scheduler.h"

#define LAYER_EXPORT __attribute__((visibility("default")))
#define NS_PER_MS 1000000ll
#define MAX_SLEEP_NS 1000000000ll   /* a request beyond this is a broken clock: internal error */

typedef struct inst_data {
    struct inst_data *next;
    void *key;
    PFN_vkGetInstanceProcAddr gipa;
    PFN_vkDestroyInstance destroy_instance;
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
    pthread_mutex_t lock;          /* guards everything below */
    int active;                    /* scheduler initialised for the current enable period */
    uint64_t generation;           /* control-channel policy generation applied */
    gfg_sched sched;
} dev_data;

static pthread_rwlock_t g_map_lock = PTHREAD_RWLOCK_INITIALIZER;
static inst_data *g_instances;
static dev_data *g_devices;
static int g_passthrough;          /* sticky; atomic access */
static int g_debug = -1;

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

static void fail(const char *why)
{
    if (!__atomic_exchange_n(&g_passthrough, 1, __ATOMIC_ACQ_REL))
        fprintf(stderr, "[gfg-pacer] internal error (%s): pass-through for this process\n", why);
}

static int64_t now_ns(void)
{
    struct timespec ts;
    if (clock_gettime(CLOCK_MONOTONIC, &ts) != 0)
        return -1;
    return (int64_t)ts.tv_sec * 1000000000ll + ts.tv_nsec;
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
    pthread_rwlock_rdlock(&g_map_lock);
    for (i = g_instances; i && i->key != key; i = i->next)
        ;
    pthread_rwlock_unlock(&g_map_lock);
    return i;
}

static dev_data *find_device(void *key)
{
    dev_data *d;
    pthread_rwlock_rdlock(&g_map_lock);
    for (d = g_devices; d && d->key != key; d = d->next)
        ;
    pthread_rwlock_unlock(&g_map_lock);
    return d;
}

/* ---- scheduler glue ---- */

/* Poll the control channel; when enabled, bring d's scheduler to the current policy (d->lock
 * held).  Returns 1 when the layer should act, 0 to forward only, -1 on an internal error. */
static int sync_policy_locked(dev_data *d, const gfg_ctl_state *st)
{
    if (!st->enabled) {
        d->active = 0;           /* re-enable starts from a fresh timeline */
        return 0;
    }
    if (!d->active) {
        gfg_sched_init(&d->sched, &st->policy);
        d->active = 1;
        d->generation = st->generation;
    } else if (d->generation != st->generation) {
        gfg_sched_set_policy(&d->sched, &st->policy);
        d->generation = st->generation;
    }
    return 1;
}

static void frame_start(dev_data *d)
{
    gfg_ctl_state st;
    int64_t now, delay, cap;
    int act;
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
    act = sync_policy_locked(d, &st);
    delay = act ? gfg_sched_frame_start(&d->sched, now) : 0;
    cap = (int64_t)(d->sched.policy.max_wait_ms * NS_PER_MS) + NS_PER_MS;
    pthread_mutex_unlock(&d->lock);
    if (delay < 0 || delay > cap) {
        fail("frame_start delay out of range");
        return;
    }
    if (delay > 0)
        sleep_until(now + delay);
}

/* Returns 1 when telemetry should be published after the present is forwarded. */
static int present_gate(dev_data *d, gfg_stats *stats)
{
    gfg_ctl_state st;
    int64_t ready, release, wait, period;
    int act;
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
    act = sync_policy_locked(d, &st);
    release = act ? gfg_sched_present(&d->sched, ready) : ready;
    period = d->sched.period_ns;
    if (act)
        *stats = *gfg_sched_stats(&d->sched);
    pthread_mutex_unlock(&d->lock);
    if (!act)
        return 0;
    wait = release - ready;
    if (wait < 0 || wait > MAX_SLEEP_NS) {
        fail("present release out of range");
        return 0;
    }
    /* Hold at most one real-frame slot: a later release only happens when the frame beat its
     * cost estimate after a capped start delay; the next slot absorbs the difference. */
    if (wait > period)
        wait = period;
    if (wait > 0)
        sleep_until(ready + wait);
    return 1;
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
    return d->acquire(device, swapchain, timeout, semaphore, fence, pImageIndex);
}

static VKAPI_ATTR VkResult VKAPI_CALL layer_AcquireNextImage2KHR(VkDevice device,
                                                                  const VkAcquireNextImageInfoKHR *info,
                                                                  uint32_t *pImageIndex)
{
    dev_data *d = find_device(dispatch_key(device));
    if (!d || !d->acquire2)
        return VK_ERROR_INITIALIZATION_FAILED;
    frame_start(d);
    return d->acquire2(device, info, pImageIndex);
}

static VKAPI_ATTR VkResult VKAPI_CALL layer_QueuePresentKHR(VkQueue queue, const VkPresentInfoKHR *info)
{
    dev_data *d = find_device(dispatch_key(queue));
    gfg_stats stats;
    if (!d || !d->present)
        return VK_ERROR_INITIALIZATION_FAILED;
    int publish = present_gate(d, &stats);
    int64_t t = now_ns();
    VkResult r = d->present(queue, info);
    if (publish)
        gfg_ctl_publish(&stats, t);
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
    pthread_rwlock_wrlock(&g_map_lock);
    i->next = g_instances;
    g_instances = i;
    pthread_rwlock_unlock(&g_map_lock);
    if (debug_on())
        fprintf(stderr, "[gfg-pacer] instance created\n");
    return VK_SUCCESS;
}

static VKAPI_ATTR void VKAPI_CALL layer_DestroyInstance(VkInstance instance, const VkAllocationCallbacks *alloc)
{
    inst_data **pp, *i = NULL;
    if (!instance)
        return;
    pthread_rwlock_wrlock(&g_map_lock);
    for (pp = &g_instances; *pp; pp = &(*pp)->next)
        if ((*pp)->key == dispatch_key(instance)) {
            i = *pp;
            *pp = i->next;
            break;
        }
    pthread_rwlock_unlock(&g_map_lock);
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
    pthread_rwlock_wrlock(&g_map_lock);
    d->next = g_devices;
    g_devices = d;
    pthread_rwlock_unlock(&g_map_lock);
    if (debug_on())
        fprintf(stderr, "[gfg-pacer] device created (swapchain hooks: %s)\n", d->present ? "yes" : "no");
    return VK_SUCCESS;
}

static VKAPI_ATTR void VKAPI_CALL layer_DestroyDevice(VkDevice device, const VkAllocationCallbacks *alloc)
{
    dev_data **pp, *d = NULL;
    if (!device)
        return;
    pthread_rwlock_wrlock(&g_map_lock);
    for (pp = &g_devices; *pp; pp = &(*pp)->next)
        if ((*pp)->key == dispatch_key(device)) {
            d = *pp;
            *pp = d->next;
            break;
        }
    pthread_rwlock_unlock(&g_map_lock);
    if (!d)
        return;
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
