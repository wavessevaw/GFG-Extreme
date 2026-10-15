/* SPDX-License-Identifier: GPL-3.0-or-later
 * GFG Native WSI: independent Vulkan-loader layer foundation.
 *
 * This stage ONLY negotiates capabilities and forwards real presentation.
 * It intentionally does NOT claim to generate or deliver synthetic frames.
 * No MAKO, LSFG, Lossless.dll, or extracted model is linked or loaded.
 * All functionality is opt-in via GFG_NATIVE_FG=1.
 */
#define _GNU_SOURCE
#include <pthread.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <vulkan/vulkan.h>
#include <vulkan/vk_layer.h>
#ifdef GFG_NATIVE_WITH_TE
#include "cpu_bridge.h"
#include "gpu_bridge.h"
#include "present_ids.h"
#endif
#include <time.h>

#define EXPORT __attribute__((visibility("default")))

typedef struct native_instance {
    struct native_instance *next;
    void *key;
    VkInstance handle;
    PFN_vkGetInstanceProcAddr gipa;
    PFN_vkDestroyInstance destroy;
    PFN_vkGetPhysicalDeviceSurfaceCapabilitiesKHR surface_caps;
    uint32_t api_version;
    int enabled;
} native_instance;

typedef struct native_queue {
    struct native_queue *next;
    VkQueue handle;
    uint32_t family;
} native_queue;

typedef struct native_swapchain {
    struct native_swapchain *next;
    VkSwapchainKHR handle;
    VkFormat format;
    VkExtent2D extent;
    uint64_t presents;
    uint64_t acquired;
    uint64_t acquire_misses;
    uint64_t present_misses;
    uint32_t image_count;
    unsigned char *owned; /* only exact acquired image indices, never fabricated */
#ifdef GFG_NATIVE_WITH_TE
    gfg_cpu_fg *bridge;
    int bridge_attempted;
    gfg_gpu_fg *gpu;
    int gpu_attempted;
    struct native_present_ids *ids; /* B4: layer-owned present ids (PRESENT_TRACE) */
#endif
    VkSwapchainCreateFlagsKHR create_flags;
    int copy_eligible; /* enabled transfer usage only; never means captured */
    VkPresentModeKHR present_mode;
    const char *path; /* "gpu", "cpu" or "none": which transport handled presents */
    double *present_us; /* GFG_NATIVE_TIMING=1: CPU time per app present */
    uint32_t present_samples;
} native_swapchain;

typedef struct native_device {
    struct native_device *next;
    void *key;
    VkDevice handle;
    VkPhysicalDevice physical;
    PFN_vkGetDeviceProcAddr gdpa;
    PFN_vkGetDeviceQueue get_queue;
    PFN_vkGetDeviceQueue2 get_queue2;
    PFN_vkDestroyDevice destroy;
    PFN_vkCreateSwapchainKHR create_swapchain;
    PFN_vkDestroySwapchainKHR destroy_swapchain;
    PFN_vkQueuePresentKHR present;
    PFN_vkGetSwapchainImagesKHR get_images;
    PFN_vkAcquireNextImageKHR acquire;
    PFN_vkAcquireNextImage2KHR acquire2;
    native_instance *instance;
    int gpu_capable;  /* external memory fd + timeline enabled by this layer */
    int semaphore_fd; /* VK_KHR_external_semaphore_fd enabled */
    int present_caps; /* NATIVE_PRESENT_* enabled (by the app or, for tracing, by us) */
    PFN_vkWaitForPresentKHR wait_present;
    PFN_vkWaitForPresent2KHR wait_present2;
    PFN_vkSetDeviceLoaderData set_loader_data; /* for layer-created command buffers */
    pthread_mutex_t lock;
    native_swapchain *swapchains;
    native_queue *queues;
} native_device;

static pthread_mutex_t map_lock = PTHREAD_MUTEX_INITIALIZER;
static native_instance *instances;
static native_device *devices;
static int trace_on = -1;

static void *dispatch_key(const void *handle) {
    return handle ? *(void *const *)handle : NULL;
}
static int tracing(void) {
    int expected = -1;
    const char *value = getenv("GFG_NATIVE_TRACE");
    (void)__atomic_compare_exchange_n(&trace_on, &expected,
        value && value[0] == '1' ? 1 : 0, 0,
        __ATOMIC_RELAXED, __ATOMIC_RELAXED);
    return __atomic_load_n(&trace_on, __ATOMIC_RELAXED);
}
static native_instance *find_instance(void *key) {
    native_instance *found = NULL;
    pthread_mutex_lock(&map_lock);
    for (native_instance *i = instances; i; i = i->next)
        if (i->key == key) { found = i; break; }
    pthread_mutex_unlock(&map_lock);
    return found;
}
static native_device *find_device(void *key) {
    native_device *found = NULL;
    pthread_mutex_lock(&map_lock);
    for (native_device *d = devices; d; d = d->next)
        if (d->key == key) { found = d; break; }
    pthread_mutex_unlock(&map_lock);
    return found;
}

static VKAPI_ATTR PFN_vkVoidFunction VKAPI_CALL
native_gipa(VkInstance instance, const char *name);
static VKAPI_ATTR PFN_vkVoidFunction VKAPI_CALL
native_gdpa(VkDevice device, const char *name);

static VKAPI_ATTR VkResult VKAPI_CALL
native_CreateInstance(const VkInstanceCreateInfo *ci,
    const VkAllocationCallbacks *alloc, VkInstance *out) {
    VkLayerInstanceCreateInfo *link = (VkLayerInstanceCreateInfo *)ci->pNext;
    while (link && !(link->sType == VK_STRUCTURE_TYPE_LOADER_INSTANCE_CREATE_INFO
                     && link->function == VK_LAYER_LINK_INFO))
        link = (VkLayerInstanceCreateInfo *)link->pNext;
    if (!link || !link->u.pLayerInfo) return VK_ERROR_INITIALIZATION_FAILED;
    PFN_vkGetInstanceProcAddr gipa = link->u.pLayerInfo->pfnNextGetInstanceProcAddr;
    link->u.pLayerInfo = link->u.pLayerInfo->pNext;
    PFN_vkCreateInstance next = (PFN_vkCreateInstance)
        gipa(VK_NULL_HANDLE, "vkCreateInstance");
    if (!next) return VK_ERROR_INITIALIZATION_FAILED;
    VkResult result = next(ci, alloc, out);
    if (result != VK_SUCCESS) return result;
    native_instance *i = calloc(1, sizeof(*i));
    PFN_vkDestroyInstance destroy = (PFN_vkDestroyInstance)
        gipa(*out, "vkDestroyInstance");
    if (!i || !destroy) {
        free(i);
        if (destroy) destroy(*out, alloc);
        return VK_ERROR_OUT_OF_HOST_MEMORY;
    }
    const char *engine = ci->pApplicationInfo
        ? ci->pApplicationInfo->pEngineName : NULL;
    const char *flag = getenv("GFG_NATIVE_FG");
    i->enabled = flag && strcmp(flag, "1") == 0 &&
        !(engine && (strcmp(engine, "gfg-temporal") == 0 ||
                     strcmp(engine, "gfg-temporal-bootstrap") == 0));
    i->handle = *out;
    i->key = dispatch_key(*out);
    i->api_version = ci->pApplicationInfo && ci->pApplicationInfo->apiVersion
        ? ci->pApplicationInfo->apiVersion : VK_API_VERSION_1_0;
    i->gipa = gipa;
    i->destroy = destroy;
    i->surface_caps = (PFN_vkGetPhysicalDeviceSurfaceCapabilitiesKHR)
        gipa(*out, "vkGetPhysicalDeviceSurfaceCapabilitiesKHR");
    pthread_mutex_lock(&map_lock);
    i->next = instances;
    instances = i;
    pthread_mutex_unlock(&map_lock);
    if (tracing())
        fprintf(stderr, "[gfg-native] instance initialized enabled=%d (WSI pass-through)\n",
                i->enabled);
    return VK_SUCCESS;
}

static VKAPI_ATTR void VKAPI_CALL
native_DestroyInstance(VkInstance instance, const VkAllocationCallbacks *alloc) {
    if (!instance) return;
    native_instance *found = NULL;
    pthread_mutex_lock(&map_lock);
    for (native_instance **p = &instances; *p; p = &(*p)->next)
        if ((*p)->key == dispatch_key(instance)) {
            found = *p; *p = found->next; break;
        }
    pthread_mutex_unlock(&map_lock);
    if (!found) return;
    found->destroy(instance, alloc);
    free(found);
}

/* GPU bridge prerequisites on the APP device: external memory fd (import of
 * TE's images), timeline semaphores, and external semaphore fd when present
 * (shared timeline; otherwise the bridge relays on a host thread).
 * Only when GFG_NATIVE_FG=1 and GFG_NATIVE_GPU_BRIDGE=1 and Vulkan >= 1.2.
 * The app's pNext chain is never rewritten: a VkPhysicalDeviceVulkan12Features
 * or VkPhysicalDeviceTimelineSemaphoreFeatures it already chains is patched
 * for the duration of the call and restored; otherwise our own timeline
 * feature struct is prepended to the (unchanged) chain. */
enum {
    NATIVE_PRESENT_ID = 1, NATIVE_PRESENT_WAIT = 2,      /* VK_KHR_present_id / _wait */
    NATIVE_PRESENT_ID2 = 4, NATIVE_PRESENT_WAIT2 = 8     /* VK_KHR_present_id2 / _wait2 */
};
typedef struct {
    VkDeviceCreateInfo ci;
    const char **extensions;
    VkPhysicalDeviceTimelineSemaphoreFeatures timeline;
    VkPhysicalDevicePresentIdFeaturesKHR present_id;
    VkPhysicalDevicePresentWaitFeaturesKHR present_wait;
    VkBool32 *patched[3];
    VkBool32 saved[3];
    int npatched;
    int active;
    int semaphore_fd;
    int present_caps; /* NATIVE_PRESENT_* enabled on the created device */
} native_device_patch;

static int native_env_is_1(const char *name) {
    const char *v = getenv(name);
    return v && v[0] == '1' && v[1] == '\0';
}
static int native_has_extension(const VkExtensionProperties *p, uint32_t n, const char *name) {
    for (uint32_t i = 0; i < n; ++i)
        if (!strcmp(p[i].extensionName, name)) return 1;
    return 0;
}
static int native_requested_extension(const VkDeviceCreateInfo *ci, const char *name) {
    for (uint32_t i = 0; i < ci->enabledExtensionCount; ++i)
        if (ci->ppEnabledExtensionNames[i] && !strcmp(ci->ppEnabledExtensionNames[i], name))
            return 1;
    return 0;
}
/* Enable a VkBool32 feature: patch the app's struct of that type for the
 * call (restored by native_unpatch_device) or prepend ours to the chain. */
static void native_enable_feature(native_device_patch *p, const VkDeviceCreateInfo *app,
        VkStructureType type, size_t offset, VkBaseOutStructure *ours) {
    for (VkBaseOutStructure *node = (VkBaseOutStructure *)app->pNext; node; node = node->pNext)
        if (node->sType == type) {
            VkBool32 *value = (VkBool32 *)((char *)node + offset);
            if (p->npatched < 3) {
                p->patched[p->npatched] = value;
                p->saved[p->npatched++] = *value;
                *value = VK_TRUE;
            }
            return;
        }
    ours->sType = type;
    ours->pNext = (VkBaseOutStructure *)p->ci.pNext;
    *(VkBool32 *)((char *)ours + offset) = VK_TRUE;
    p->ci.pNext = ours;
}
static int native_chained_feature(const VkDeviceCreateInfo *ci, VkStructureType type, size_t offset) {
    for (const VkBaseInStructure *node = ci->pNext; node; node = node->pNext)
        if (node->sType == type) return *(const VkBool32 *)((const char *)node + offset) == VK_TRUE;
    return 0;
}

static const char *native_patch_device(native_instance *inst, VkPhysicalDevice phys,
        const VkDeviceCreateInfo *ci, native_device_patch *p) {
    memset(p, 0, sizeof(*p));
    p->ci = *ci;
#ifndef GFG_NATIVE_WITH_TE
    (void)inst; (void)phys;
    return "built-without-te";
#endif
    if (!inst || !inst->enabled) return "layer-not-enabled";
    if (!native_env_is_1("GFG_NATIVE_GPU_BRIDGE")) return "gpu-bridge-not-requested";
    if (inst->api_version < VK_API_VERSION_1_2) return "instance-api-below-1.2";
    PFN_vkGetPhysicalDeviceProperties props = (PFN_vkGetPhysicalDeviceProperties)
        inst->gipa(inst->handle, "vkGetPhysicalDeviceProperties");
    PFN_vkGetPhysicalDeviceFeatures2 feats2 = (PFN_vkGetPhysicalDeviceFeatures2)
        inst->gipa(inst->handle, "vkGetPhysicalDeviceFeatures2");
    PFN_vkEnumerateDeviceExtensionProperties enumerate =
        (PFN_vkEnumerateDeviceExtensionProperties)
        inst->gipa(inst->handle, "vkEnumerateDeviceExtensionProperties");
    if (!props || !feats2 || !enumerate) return "entrypoints";
    VkPhysicalDeviceProperties pp;
    props(phys, &pp);
    if (pp.apiVersion < VK_API_VERSION_1_2) return "device-api-below-1.2";
    VkPhysicalDeviceTimelineSemaphoreFeatures tf = {
        .sType = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_TIMELINE_SEMAPHORE_FEATURES};
    VkPhysicalDeviceFeatures2 f2 = {.sType = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_FEATURES_2,
        .pNext = &tf};
    feats2(phys, &f2);
    if (!tf.timelineSemaphore) return "no-timeline-semaphore";
    uint32_t n = 0;
    if (enumerate(phys, NULL, &n, NULL) != VK_SUCCESS || !n) return "extension-query";
    VkExtensionProperties *ext = calloc(n, sizeof(*ext));
    if (!ext) return "oom";
    if (enumerate(phys, NULL, &n, ext) != VK_SUCCESS) { free(ext); return "extension-query"; }
    const int mem_fd = native_has_extension(ext, n, VK_KHR_EXTERNAL_MEMORY_FD_EXTENSION_NAME);
    const int sem_fd = native_has_extension(ext, n, VK_KHR_EXTERNAL_SEMAPHORE_FD_EXTENSION_NAME);
    const int has_pid = native_has_extension(ext, n, VK_KHR_PRESENT_ID_EXTENSION_NAME);
    const int has_pwait = native_has_extension(ext, n, VK_KHR_PRESENT_WAIT_EXTENSION_NAME);
    free(ext);
    if (!mem_fd) return "no-external-memory-fd";
    /* What the app itself enabled (extension + feature bit). */
    if (native_requested_extension(ci, VK_KHR_PRESENT_ID_EXTENSION_NAME) &&
        native_chained_feature(ci, VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_PRESENT_ID_FEATURES_KHR,
                               offsetof(VkPhysicalDevicePresentIdFeaturesKHR, presentId)))
        p->present_caps |= NATIVE_PRESENT_ID;
    if (native_requested_extension(ci, VK_KHR_PRESENT_WAIT_EXTENSION_NAME) &&
        native_chained_feature(ci, VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_PRESENT_WAIT_FEATURES_KHR,
                               offsetof(VkPhysicalDevicePresentWaitFeaturesKHR, presentWait)))
        p->present_caps |= NATIVE_PRESENT_WAIT;
    if (native_requested_extension(ci, VK_KHR_PRESENT_ID_2_EXTENSION_NAME) &&
        native_chained_feature(ci, VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_PRESENT_ID_2_FEATURES_KHR,
                               offsetof(VkPhysicalDevicePresentId2FeaturesKHR, presentId2)))
        p->present_caps |= NATIVE_PRESENT_ID2;
    if (native_requested_extension(ci, VK_KHR_PRESENT_WAIT_2_EXTENSION_NAME) &&
        native_chained_feature(ci, VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_PRESENT_WAIT_2_FEATURES_KHR,
                               offsetof(VkPhysicalDevicePresentWait2FeaturesKHR, presentWait2)))
        p->present_caps |= NATIVE_PRESENT_WAIT2;
    /* GFG_NATIVE_PRESENT_TRACE=1: enable v1 present id/wait ourselves when
     * supported and not already enabled (presented-frame instrumentation). */
    int add_pid = 0, add_pwait = 0;
    if (native_env_is_1("GFG_NATIVE_PRESENT_TRACE") && has_pid && has_pwait) {
        VkPhysicalDevicePresentIdFeaturesKHR qid = {
            .sType = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_PRESENT_ID_FEATURES_KHR};
        VkPhysicalDevicePresentWaitFeaturesKHR qwait = {
            .sType = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_PRESENT_WAIT_FEATURES_KHR, .pNext = &qid};
        VkPhysicalDeviceFeatures2 q2 = {.sType = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_FEATURES_2,
            .pNext = &qwait};
        feats2(phys, &q2);
        if (qid.presentId && qwait.presentWait) {
            add_pid = !(p->present_caps & NATIVE_PRESENT_ID);
            add_pwait = !(p->present_caps & NATIVE_PRESENT_WAIT);
        }
    }
    p->extensions = calloc(ci->enabledExtensionCount + 4u, sizeof(char *));
    if (!p->extensions) return "oom";
    uint32_t count = 0;
    for (uint32_t i = 0; i < ci->enabledExtensionCount; ++i)
        p->extensions[count++] = ci->ppEnabledExtensionNames[i];
    if (!native_requested_extension(ci, VK_KHR_EXTERNAL_MEMORY_FD_EXTENSION_NAME))
        p->extensions[count++] = VK_KHR_EXTERNAL_MEMORY_FD_EXTENSION_NAME;
    if (sem_fd && !native_requested_extension(ci, VK_KHR_EXTERNAL_SEMAPHORE_FD_EXTENSION_NAME))
        p->extensions[count++] = VK_KHR_EXTERNAL_SEMAPHORE_FD_EXTENSION_NAME;
    if (add_pid && !native_requested_extension(ci, VK_KHR_PRESENT_ID_EXTENSION_NAME))
        p->extensions[count++] = VK_KHR_PRESENT_ID_EXTENSION_NAME;
    if (add_pwait && !native_requested_extension(ci, VK_KHR_PRESENT_WAIT_EXTENSION_NAME))
        p->extensions[count++] = VK_KHR_PRESENT_WAIT_EXTENSION_NAME;
    p->ci.enabledExtensionCount = count;
    p->ci.ppEnabledExtensionNames = p->extensions;
    /* timelineSemaphore: an app Vulkan12Features struct forbids also
     * chaining the individual struct, so patch whichever the app has */
    int vk12 = 0;
    for (const VkBaseInStructure *node = ci->pNext; node; node = node->pNext)
        if (node->sType == VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_VULKAN_1_2_FEATURES) vk12 = 1;
    if (vk12)
        native_enable_feature(p, ci, VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_VULKAN_1_2_FEATURES,
            offsetof(VkPhysicalDeviceVulkan12Features, timelineSemaphore),
            (VkBaseOutStructure *)&p->timeline /* never used: the app has one */);
    else
        native_enable_feature(p, ci, VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_TIMELINE_SEMAPHORE_FEATURES,
            offsetof(VkPhysicalDeviceTimelineSemaphoreFeatures, timelineSemaphore),
            (VkBaseOutStructure *)&p->timeline);
    if (add_pid) {
        native_enable_feature(p, ci, VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_PRESENT_ID_FEATURES_KHR,
            offsetof(VkPhysicalDevicePresentIdFeaturesKHR, presentId),
            (VkBaseOutStructure *)&p->present_id);
        p->present_caps |= NATIVE_PRESENT_ID;
    }
    if (add_pwait) {
        native_enable_feature(p, ci, VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_PRESENT_WAIT_FEATURES_KHR,
            offsetof(VkPhysicalDevicePresentWaitFeaturesKHR, presentWait),
            (VkBaseOutStructure *)&p->present_wait);
        p->present_caps |= NATIVE_PRESENT_WAIT;
    }
    p->active = 1;
    p->semaphore_fd = sem_fd;
    return NULL;
}
static void native_unpatch_device(native_device_patch *p) {
    for (int i = 0; i < p->npatched; ++i) *p->patched[i] = p->saved[i];
    p->npatched = 0;
    free(p->extensions);
    p->extensions = NULL;
}

static VKAPI_ATTR VkResult VKAPI_CALL
native_CreateDevice(VkPhysicalDevice phys, const VkDeviceCreateInfo *ci,
    const VkAllocationCallbacks *alloc, VkDevice *out) {
    VkLayerDeviceCreateInfo *link = (VkLayerDeviceCreateInfo *)ci->pNext;
    while (link && !(link->sType == VK_STRUCTURE_TYPE_LOADER_DEVICE_CREATE_INFO
                     && link->function == VK_LAYER_LINK_INFO))
        link = (VkLayerDeviceCreateInfo *)link->pNext;
    if (!link || !link->u.pLayerInfo) return VK_ERROR_INITIALIZATION_FAILED;
    PFN_vkGetInstanceProcAddr gipa = link->u.pLayerInfo->pfnNextGetInstanceProcAddr;
    PFN_vkGetDeviceProcAddr gdpa = link->u.pLayerInfo->pfnNextGetDeviceProcAddr;
    PFN_vkSetDeviceLoaderData set_loader_data = NULL;
    for (VkLayerDeviceCreateInfo *cb = (VkLayerDeviceCreateInfo *)ci->pNext; cb;
         cb = (VkLayerDeviceCreateInfo *)cb->pNext)
        if (cb->sType == VK_STRUCTURE_TYPE_LOADER_DEVICE_CREATE_INFO &&
            cb->function == VK_LOADER_DATA_CALLBACK) {
            set_loader_data = cb->u.pfnSetDeviceLoaderData;
            break;
        }
    link->u.pLayerInfo = link->u.pLayerInfo->pNext;
    PFN_vkCreateDevice next = (PFN_vkCreateDevice)
        gipa(VK_NULL_HANDLE, "vkCreateDevice");
    if (!next) return VK_ERROR_INITIALIZATION_FAILED;
    native_device_patch patch;
    const char *patch_reason = native_patch_device(find_instance(dispatch_key(phys)),
                                                   phys, ci, &patch);
    VkResult result = next(phys, patch.active ? &patch.ci : ci, alloc, out);
    const int gpu_capable = patch.active && result == VK_SUCCESS;
    const int semaphore_fd = gpu_capable && patch.semaphore_fd;
    const int present_caps = gpu_capable ? patch.present_caps : 0;
    const int patched = patch.active;
    native_unpatch_device(&patch);
    if (patched && result != VK_SUCCESS) {
        /* Never prevent the game's own device: retry exactly as requested. */
        patch_reason = "patched-create-failed";
        result = next(phys, ci, alloc, out);
    }
    if (tracing())
        fprintf(stderr, "[gfg-native] device gpu_bridge_capable=%d semaphore_fd=%d"
                " present_caps=0x%x reason=%s\n", gpu_capable, semaphore_fd, present_caps,
                patch_reason ? patch_reason : "enabled");
    if (result != VK_SUCCESS) return result;
    native_device *d = calloc(1, sizeof(*d));
    PFN_vkDestroyDevice destroy = (PFN_vkDestroyDevice)
        gdpa(*out, "vkDestroyDevice");
    if (!d || !destroy) {
        free(d);
        if (destroy) destroy(*out, alloc);
        return VK_ERROR_OUT_OF_HOST_MEMORY;
    }
    if (pthread_mutex_init(&d->lock, NULL) != 0) {
        destroy(*out, alloc); free(d);
        return VK_ERROR_INITIALIZATION_FAILED;
    }
    d->handle = *out;
    d->key = dispatch_key(*out);
    d->physical = phys;
    d->gpu_capable = gpu_capable;
    d->set_loader_data = set_loader_data;
    d->semaphore_fd = semaphore_fd;
    d->present_caps = present_caps;
    d->gdpa = gdpa;
    d->destroy = destroy;
    d->get_queue = (PFN_vkGetDeviceQueue)gdpa(*out, "vkGetDeviceQueue");
    d->get_queue2 = (PFN_vkGetDeviceQueue2)gdpa(*out, "vkGetDeviceQueue2");
    d->create_swapchain = (PFN_vkCreateSwapchainKHR)
        gdpa(*out, "vkCreateSwapchainKHR");
    d->destroy_swapchain = (PFN_vkDestroySwapchainKHR)
        gdpa(*out, "vkDestroySwapchainKHR");
    d->present = (PFN_vkQueuePresentKHR)
        gdpa(*out, "vkQueuePresentKHR");
    d->get_images = (PFN_vkGetSwapchainImagesKHR)
        gdpa(*out, "vkGetSwapchainImagesKHR");
    d->acquire = (PFN_vkAcquireNextImageKHR)
        gdpa(*out, "vkAcquireNextImageKHR");
    d->wait_present = (PFN_vkWaitForPresentKHR)gdpa(*out, "vkWaitForPresentKHR");
    d->wait_present2 = (PFN_vkWaitForPresent2KHR)gdpa(*out, "vkWaitForPresent2KHR");
    d->acquire2 = (PFN_vkAcquireNextImage2KHR)
        gdpa(*out, "vkAcquireNextImage2KHR");
    pthread_mutex_lock(&map_lock);
    for (native_instance *i = instances; i; i = i->next)
        if (i->key == dispatch_key(phys)) {
            d->instance = i; break;
        }
    d->next = devices;
    devices = d;
    pthread_mutex_unlock(&map_lock);
    return VK_SUCCESS;
}

#ifdef GFG_NATIVE_WITH_TE
/* ---- B4: layer-owned present ids + optional presentation monitor ----
 * Active only with GFG_NATIVE_PRESENT_TRACE=1 on a GPU-bridge swapchain whose
 * device has present ids enabled. Every present the bridge issues gets a
 * fresh layer id; the app's own ids are mapped (present_ids.h) and its
 * vkWaitForPresent(2)KHR calls translated, so its semantics hold. */
#define NATIVE_MONITOR_QUEUE 256u
typedef struct native_present_ids {
    pthread_mutex_t lock;
    pthread_cond_t cond;          /* CLOCK_MONOTONIC */
    gfg_present_map map;
    int mode;                     /* 1 VkPresentIdKHR, 2 VkPresentId2KHR */
    int wait_mode;                /* 0 none, 1 vkWaitForPresentKHR, 2 vkWaitForPresent2KHR */
    VkDevice device;
    VkSwapchainKHR swapchain;
    PFN_vkWaitForPresentKHR wait1;
    PFN_vkWaitForPresent2KHR wait2;
    int monitor_started;
    int stop;
    pthread_t thread;
    uint64_t queue_id[NATIVE_MONITOR_QUEUE];
    int queue_kind[NATIVE_MONITOR_QUEUE];
    uint32_t qhead, qcount;
    uint64_t dropped, done, last_done_ns;
} native_present_ids;

static uint64_t native_now_ns(void) {
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return (uint64_t)t.tv_sec * 1000000000ull + (uint64_t)t.tv_nsec;
}
static VkResult native_ids_driver_wait(native_present_ids *ids, uint64_t id, uint64_t timeout) {
    if (ids->wait_mode == 2) {
        VkPresentWait2InfoKHR wi = {.sType = VK_STRUCTURE_TYPE_PRESENT_WAIT_2_INFO_KHR,
            .presentId = id, .timeout = timeout};
        return ids->wait2(ids->device, ids->swapchain, &wi);
    }
    return ids->wait1(ids->device, ids->swapchain, id, timeout);
}
static void *native_monitor_main(void *arg) {
    native_present_ids *ids = arg;
    static const char *kinds[4] = {"R", "G1", "G2", "D"};
    pthread_mutex_lock(&ids->lock);
    for (;;) {
        while (!ids->qcount && !ids->stop) pthread_cond_wait(&ids->cond, &ids->lock);
        if (ids->stop) break;
        const uint64_t id = ids->queue_id[ids->qhead];
        const int kind = ids->queue_kind[ids->qhead];
        pthread_mutex_unlock(&ids->lock);
        VkResult r;
        do {
            r = native_ids_driver_wait(ids, id, 100000000ull);
        } while (r == VK_TIMEOUT && !__atomic_load_n(&ids->stop, __ATOMIC_RELAXED));
        const uint64_t t = native_now_ns();
        if (r == VK_SUCCESS) {
            fprintf(stderr, "[gfg-native] present_done id=%llu kind=%s t_ns=%llu dt_us=%.1f\n",
                    (unsigned long long)id, kinds[kind < 4 && kind >= 0 ? kind : 0],
                    (unsigned long long)t,
                    ids->last_done_ns ? (double)(t - ids->last_done_ns) / 1000.0 : 0.0);
            ids->last_done_ns = t;
        } else if (r != VK_TIMEOUT) {
            fprintf(stderr, "[gfg-native] present_wait id=%llu kind=%s vkresult=%d\n",
                    (unsigned long long)id, kinds[kind < 4 && kind >= 0 ? kind : 0], (int)r);
        }
        pthread_mutex_lock(&ids->lock);
        if (r == VK_SUCCESS) ++ids->done;
        ids->qhead = (ids->qhead + 1) % NATIVE_MONITOR_QUEUE;
        --ids->qcount;
    }
    pthread_mutex_unlock(&ids->lock);
    return NULL;
}
static uint64_t native_ids_assign(void *user, int kind, uint64_t app_id) {
    native_present_ids *ids = user;
    pthread_mutex_lock(&ids->lock);
    const uint64_t id = gfg_pm_next(&ids->map);
    if (kind == 0) gfg_pm_map(&ids->map, app_id, id);
    if (ids->monitor_started) {
        if (ids->qcount < NATIVE_MONITOR_QUEUE) {
            const uint32_t slot = (ids->qhead + ids->qcount++) % NATIVE_MONITOR_QUEUE;
            ids->queue_id[slot] = id;
            ids->queue_kind[slot] = kind;
        } else {
            ++ids->dropped;
        }
    }
    pthread_cond_broadcast(&ids->cond);
    pthread_mutex_unlock(&ids->lock);
    return id;
}
static native_present_ids *native_ids_create(native_device *d, native_swapchain *sc) {
    if (!native_env_is_1("GFG_NATIVE_PRESENT_TRACE")) return NULL;
    int mode = 0, wait_mode = 0;
    if ((sc->create_flags & VK_SWAPCHAIN_CREATE_PRESENT_ID_2_BIT_KHR) &&
        (d->present_caps & NATIVE_PRESENT_ID2)) {
        mode = 2;
        if ((sc->create_flags & VK_SWAPCHAIN_CREATE_PRESENT_WAIT_2_BIT_KHR) &&
            (d->present_caps & NATIVE_PRESENT_WAIT2) && d->wait_present2)
            wait_mode = 2;
    } else if (d->present_caps & NATIVE_PRESENT_ID) {
        mode = 1;
        if ((d->present_caps & NATIVE_PRESENT_WAIT) && d->wait_present) wait_mode = 1;
    }
    fprintf(stderr, "[gfg-native] present-ids mode=%d monitor=%d (present_caps=0x%x)\n",
            mode, wait_mode, d->present_caps);
    if (!mode) return NULL;
    native_present_ids *ids = calloc(1, sizeof(*ids));
    if (!ids) return NULL;
    pthread_condattr_t ca;
    pthread_condattr_init(&ca);
    pthread_condattr_setclock(&ca, CLOCK_MONOTONIC);
    pthread_mutex_init(&ids->lock, NULL);
    pthread_cond_init(&ids->cond, &ca);
    pthread_condattr_destroy(&ca);
    ids->mode = mode;
    ids->wait_mode = wait_mode;
    ids->device = d->handle;
    ids->swapchain = sc->handle;
    ids->wait1 = d->wait_present;
    ids->wait2 = d->wait_present2;
    if (wait_mode && pthread_create(&ids->thread, NULL, native_monitor_main, ids) == 0)
        ids->monitor_started = 1;
    return ids;
}
static void native_ids_destroy(native_present_ids *ids) {
    if (!ids) return;
    pthread_mutex_lock(&ids->lock);
    __atomic_store_n(&ids->stop, 1, __ATOMIC_RELAXED);
    pthread_cond_broadcast(&ids->cond);
    pthread_mutex_unlock(&ids->lock);
    if (ids->monitor_started) pthread_join(ids->thread, NULL);
    fprintf(stderr, "[gfg-native] present-ids retired last_layer_id=%llu last_app_id=%llu"
            " monitored_done=%llu dropped=%llu\n",
            (unsigned long long)ids->map.last_layer, (unsigned long long)ids->map.last_app,
            (unsigned long long)ids->done, (unsigned long long)ids->dropped);
    pthread_cond_destroy(&ids->cond);
    pthread_mutex_destroy(&ids->lock);
    free(ids);
}
/* app id -> layer id; waits (bounded by timeout) for the app's present */
static VkResult native_ids_translate(native_present_ids *ids, uint64_t app_id, uint64_t timeout,
                                     uint64_t *layer_id, uint64_t *remaining) {
    const uint64_t start = native_now_ns();
    VkResult r = VK_SUCCESS;
    pthread_mutex_lock(&ids->lock);
    while (!gfg_pm_translate(&ids->map, app_id, layer_id)) {
        if (timeout == 0) { r = VK_TIMEOUT; break; }
        if (timeout == UINT64_MAX) {
            pthread_cond_wait(&ids->cond, &ids->lock);
            continue;
        }
        const uint64_t elapsed = native_now_ns() - start;
        if (elapsed >= timeout) { r = VK_TIMEOUT; break; }
        struct timespec until;
        clock_gettime(CLOCK_MONOTONIC, &until);
        const uint64_t left = timeout - elapsed;
        until.tv_sec += (time_t)(left / 1000000000ull);
        until.tv_nsec += (long)(left % 1000000000ull);
        if (until.tv_nsec >= 1000000000L) { until.tv_sec++; until.tv_nsec -= 1000000000L; }
        pthread_cond_timedwait(&ids->cond, &ids->lock, &until);
    }
    pthread_mutex_unlock(&ids->lock);
    if (timeout == UINT64_MAX) *remaining = UINT64_MAX;
    else {
        const uint64_t elapsed = native_now_ns() - start;
        *remaining = elapsed < timeout ? timeout - elapsed : 0;
    }
    return r;
}
#endif

#define NATIVE_TIMING_CAP 8192
static int native_cmp_double(const void *a, const void *b) {
    const double x = *(const double *)a, y = *(const double *)b;
    return x < y ? -1 : x > y;
}
static void native_swapchain_free(native_swapchain *sc) {
    if (sc->present_us && sc->present_samples > 2) {
        /* the first two presents carry one-time bridge creation; excluded */
        const uint32_t n = sc->present_samples - 2;
        double *v = sc->present_us + 2;
        qsort(v, n, sizeof(double), native_cmp_double);
        fprintf(stderr,
            "[gfg-native] present-timing path=%s %ux%u frames=%u median_us=%.1f p95_us=%.1f"
            " max_us=%.1f (CPU time inside the layer's vkQueuePresentKHR, incl. downstream presents)\n",
            sc->path ? sc->path : "none", sc->extent.width, sc->extent.height, n,
            v[n / 2], v[(uint32_t)((n - 1) * 0.95)], v[n - 1]);
    }
#ifdef GFG_NATIVE_WITH_TE
    if (sc->bridge) gfg_cpu_fg_destroy(sc->bridge);
    if (sc->gpu) gfg_gpu_fg_destroy(sc->gpu);
    native_ids_destroy(sc->ids); /* stops the monitor before the swapchain goes */
#endif
    free(sc->present_us);
    free(sc->owned);
    free(sc);
}

static VKAPI_ATTR void VKAPI_CALL
native_DestroyDevice(VkDevice device, const VkAllocationCallbacks *alloc) {
    if (!device) return;
    native_device *found = NULL;
    pthread_mutex_lock(&map_lock);
    for (native_device **p = &devices; *p; p = &(*p)->next)
        if ((*p)->key == dispatch_key(device)) {
            found = *p; *p = found->next; break;
        }
    pthread_mutex_unlock(&map_lock);
    if (!found) return;
    native_swapchain *sc = found->swapchains;
    while (sc) {
        native_swapchain *next = sc->next;
        native_swapchain_free(sc);
        sc = next;
    }
    native_queue *queue = found->queues;
    while (queue) {
        native_queue *next = queue->next;
        free(queue);
        queue = next;
    }
    found->destroy(device, alloc);
    pthread_mutex_destroy(&found->lock);
    free(found);
}

static int native_supported_sdr8_format(VkFormat format) {
    /* CPU transport handles byte-valued SDR images. SRGB is a transfer
       function, not a different channel count or per-pixel memory layout. */
    return format == VK_FORMAT_R8G8B8A8_UNORM ||
           format == VK_FORMAT_B8G8R8A8_UNORM ||
           format == VK_FORMAT_R8G8B8A8_SRGB ||
           format == VK_FORMAT_B8G8R8A8_SRGB;
}

static const char *native_ineligible_reason(const VkSwapchainCreateInfoKHR *ci) {
    /* These two flags select the game's presentation-ID and wait protocol.
     * They do NOT request protected memory or a different image layout.
     * Preserve them, and all original pNext structures, unchanged.
     * Never open the gate for protected or other unverified flag bits. */
    const VkSwapchainCreateFlagsKHR present_protocol =
        VK_SWAPCHAIN_CREATE_PRESENT_ID_2_BIT_KHR |
        VK_SWAPCHAIN_CREATE_PRESENT_WAIT_2_BIT_KHR;
    if (ci->flags & ~present_protocol)
        return "unsupported-swapchain-flags";
    if (ci->imageArrayLayers != 1) return "array-layers";
    if (ci->imageSharingMode != VK_SHARING_MODE_EXCLUSIVE) return "sharing-mode";
    if (!ci->imageExtent.width || !ci->imageExtent.height) return "zero-extent";
    if (!native_supported_sdr8_format(ci->imageFormat))
        return "unsupported-format";
    return NULL;
}

static int native_copy_usage_ready(VkImageUsageFlags usage) {
    const VkImageUsageFlags wanted =
        VK_IMAGE_USAGE_TRANSFER_SRC_BIT | VK_IMAGE_USAGE_TRANSFER_DST_BIT;
    return (usage & wanted) == wanted;
}

static void native_record_queue(native_device *d, VkQueue queue, uint32_t family) {
    if (!queue) return;
    pthread_mutex_lock(&d->lock);
    for (native_queue *node = d->queues; node; node = node->next)
        if (node->handle == queue) {
            node->family = family;
            pthread_mutex_unlock(&d->lock);
            return;
        }
    native_queue *node = calloc(1, sizeof(*node));
    if (node) {
        node->handle = queue;
        node->family = family;
        node->next = d->queues;
        d->queues = node;
    }
    pthread_mutex_unlock(&d->lock);
}
static VKAPI_ATTR void VKAPI_CALL
native_GetDeviceQueue(VkDevice device, uint32_t family, uint32_t index,
        VkQueue *queue) {
    native_device *d = find_device(dispatch_key(device));
    if (!d || !d->get_queue) return;
    d->get_queue(device, family, index, queue);
    if (queue) native_record_queue(d, *queue, family);
}
static VKAPI_ATTR void VKAPI_CALL
native_GetDeviceQueue2(VkDevice device, const VkDeviceQueueInfo2 *info,
        VkQueue *queue) {
    native_device *d = find_device(dispatch_key(device));
    if (!d || !d->get_queue2) return;
    d->get_queue2(device, info, queue);
    if (queue && info) native_record_queue(d, *queue, info->queueFamilyIndex);
}

static VKAPI_ATTR VkResult VKAPI_CALL
native_CreateSwapchainKHR(VkDevice device, const VkSwapchainCreateInfoKHR *ci,
    const VkAllocationCallbacks *alloc, VkSwapchainKHR *out) {
    native_device *d = find_device(dispatch_key(device));
    if (!d || !d->create_swapchain || !ci || !out)
        return VK_ERROR_INITIALIZATION_FAILED;
    int candidate = 0;
    const char *reason = NULL;
    VkImageUsageFlags supported_usage = 0;
    int caps_queried = 0;
    VkResult caps_result = VK_SUCCESS;
    VkResult extended_result = VK_SUCCESS;
    VkSwapchainCreateInfoKHR extended = *ci;
    VkSurfaceCapabilitiesKHR caps = {0};
    if (!d->instance || !d->instance->enabled) {
        reason = "layer-not-enabled";
    } else if ((reason = native_ineligible_reason(ci)) != NULL) {
        /* Keep the original WSI path untouched on unsupported shapes. */
    } else if (native_copy_usage_ready(ci->imageUsage)) {
        /* The game already requested both copy operations. Keep its
         * flags, pNext and usage; only the image count grows (below). */
        candidate = 1;
        reason = "existing-usage-ready";
    } else if (!d->instance->surface_caps) {
        reason = "surface-capabilities-entrypoint-missing";
    } else {
        caps_queried = 1;
        caps_result = d->instance->surface_caps(d->physical, ci->surface, &caps);
        supported_usage = caps.supportedUsageFlags;
        const VkImageUsageFlags wanted =
            VK_IMAGE_USAGE_TRANSFER_SRC_BIT | VK_IMAGE_USAGE_TRANSFER_DST_BIT;
        if (caps_result != VK_SUCCESS) {
            reason = "surface-capabilities-query-failed";
        } else if ((caps.supportedUsageFlags & wanted) != wanted) {
            reason = "missing-transfer-src-or-dst-support";
        } else {
            extended.imageUsage |= wanted;
            candidate = 1;
            reason = "extended-usage-ready";
        }
    }
    if (candidate) {
        /* Two synthetic presents per real frame need two spare images
         * beyond what the game keeps acquired (B3). The game still sees the
         * real count from vkGetSwapchainImagesKHR and indexes what it acquires. */
        if (!caps_queried && d->instance->surface_caps) {
            caps_queried = 1;
            caps_result = d->instance->surface_caps(d->physical, ci->surface, &caps);
        }
        uint32_t wanted_images = ci->minImageCount + 2u;
        if (caps_queried && caps_result == VK_SUCCESS && caps.maxImageCount &&
                wanted_images > caps.maxImageCount)
            wanted_images = caps.maxImageCount;
        if (wanted_images > extended.minImageCount) extended.minImageCount = wanted_images;
    }
    VkResult result = d->create_swapchain(device, candidate ? &extended : ci,
                                           alloc, out);
    if (result != VK_SUCCESS && candidate) {
        // Never prevent a game from creating its original swapchain.
        extended_result = result;
        reason = "extended-create-failed";
        candidate = 0;
        *out = VK_NULL_HANDLE;
        result = d->create_swapchain(device, ci, alloc, out);
    }
    if (result != VK_SUCCESS) return result;
    native_swapchain *sc = calloc(1, sizeof(*sc));
    if (!sc) {
        // The swapchain is valid, but native recording is unavailable.
        // Forwarding is still safe; no bookkeeping means no generation.
        return VK_SUCCESS;
    }
    sc->handle = *out;
    sc->format = ci->imageFormat;
    sc->extent = ci->imageExtent;
    sc->copy_eligible = candidate;
    sc->present_mode = ci->presentMode;
    sc->create_flags = ci->flags;
    {
        const char *timing = getenv("GFG_NATIVE_TIMING");
        if (timing && timing[0] == '1')
            sc->present_us = calloc(NATIVE_TIMING_CAP, sizeof(double));
    }
    if (d->get_images) {
        uint32_t image_count = 0;
        if (d->get_images(device, *out, &image_count, NULL) == VK_SUCCESS &&
                image_count > 0 && image_count <= 256) {
            sc->owned = calloc(image_count, sizeof(*sc->owned));
            if (sc->owned) sc->image_count = image_count;
        }
    }
    pthread_mutex_lock(&d->lock);
    sc->next = d->swapchains;
    d->swapchains = sc;
    pthread_mutex_unlock(&d->lock);
    if (tracing())
        fprintf(stderr,
            "[gfg-native] swapchain %ux%u candidate=%d output=real-only"
            " reason=%s format=%d flags=0x%x layers=%u sharing=%d"
            " requested_usage=0x%x supported_usage=0x%x caps_queried=%d"
            " caps_result=%d extended_result=%d min_images=%u->%u images=%u present_mode=%d\n",
            sc->extent.width, sc->extent.height, sc->copy_eligible,
            reason ? reason : "accepted", (int)ci->imageFormat,
            (unsigned)ci->flags, ci->imageArrayLayers,
            (int)ci->imageSharingMode, (unsigned)ci->imageUsage,
            (unsigned)supported_usage, caps_queried,
            (int)caps_result, (int)extended_result, ci->minImageCount,
            candidate ? extended.minImageCount : ci->minImageCount, sc->image_count,
            (int)ci->presentMode);
    return VK_SUCCESS;
}

static VKAPI_ATTR void VKAPI_CALL
native_DestroySwapchainKHR(VkDevice device, VkSwapchainKHR sc,
    const VkAllocationCallbacks *alloc) {
    native_device *d = find_device(dispatch_key(device));
    if (!d || !d->destroy_swapchain) return;
    pthread_mutex_lock(&d->lock);
    for (native_swapchain **p = &d->swapchains; *p; p = &(*p)->next)
        if ((*p)->handle == sc) {
            native_swapchain *old = *p;
            *p = old->next;
            native_swapchain_free(old);
            break;
        }
    pthread_mutex_unlock(&d->lock);
    d->destroy_swapchain(device, sc, alloc);
}

static void native_acquired(native_device *d, VkSwapchainKHR handle, uint32_t index) {
    pthread_mutex_lock(&d->lock);
    for (native_swapchain *sc = d->swapchains; sc; sc = sc->next) {
        if (sc->handle != handle) continue;
        if (!sc->owned || index >= sc->image_count || sc->owned[index]) {
            ++sc->acquire_misses;
        } else {
            sc->owned[index] = 1;
            ++sc->acquired;
        }
        break;
    }
    pthread_mutex_unlock(&d->lock);
}

static VKAPI_ATTR VkResult VKAPI_CALL
native_AcquireNextImageKHR(VkDevice device, VkSwapchainKHR swapchain,
        uint64_t timeout, VkSemaphore semaphore, VkFence fence, uint32_t *index) {
    native_device *d = find_device(dispatch_key(device));
    if (!d || !d->acquire) return VK_ERROR_INITIALIZATION_FAILED;
    VkResult result = d->acquire(device, swapchain, timeout, semaphore, fence, index);
    if ((result == VK_SUCCESS || result == VK_SUBOPTIMAL_KHR) && index)
        native_acquired(d, swapchain, *index);
    return result;
}

static VKAPI_ATTR VkResult VKAPI_CALL
native_AcquireNextImage2KHR(VkDevice device, const VkAcquireNextImageInfoKHR *info,
        uint32_t *index) {
    native_device *d = find_device(dispatch_key(device));
    if (!d || !d->acquire2) return VK_ERROR_INITIALIZATION_FAILED;
    VkResult result = d->acquire2(device, info, index);
    if ((result == VK_SUCCESS || result == VK_SUBOPTIMAL_KHR) && index && info)
        native_acquired(d, info->swapchain, *index);
    return result;
}

static VKAPI_ATTR VkResult VKAPI_CALL
native_QueuePresentKHR(VkQueue queue, const VkPresentInfoKHR *info) {
    native_device *d = find_device(dispatch_key(queue));
    if (!d || !d->present) return VK_ERROR_INITIALIZATION_FAILED;
    // Observe acquisition ownership. Do NOT consume the application's semaphores
    // or mutate VkPresentInfoKHR; those belong to the game/real-frame path.
    if (info && info->pImageIndices && info->pSwapchains) {
        pthread_mutex_lock(&d->lock);
        for (uint32_t n = 0; n < info->swapchainCount; ++n) {
            for (native_swapchain *sc = d->swapchains; sc; sc = sc->next) {
                if (sc->handle != info->pSwapchains[n]) continue;
                const uint32_t idx = info->pImageIndices[n];
                if (!sc->owned || idx >= sc->image_count || !sc->owned[idx])
                    ++sc->present_misses;
                else sc->owned[idx] = 0;
                break;
            }
        }
        pthread_mutex_unlock(&d->lock);
    }
    // Exactly one forward: no synthetic present or extra swapchain acquisition
    // until the independent image/queue/timeline ownership contract is proven.
    VkResult result;
    struct timespec present_start;
    clock_gettime(CLOCK_MONOTONIC, &present_start);
    const char *path = "none";
#ifdef GFG_NATIVE_WITH_TE
    gfg_cpu_fg *bridge = NULL;
    gfg_gpu_fg *gpu = NULL;
    gfg_present_id_hooks ids = {0};
    const char *flag = getenv("GFG_NATIVE_CPU_BRIDGE");
    /* GPU bridge takes precedence; when requested it never falls back to
     * the CPU bridge (a failed GPU bridge means real-frame pass-through). */
    const int want_gpu = native_env_is_1("GFG_NATIVE_GPU_BRIDGE");
    if (want_gpu && info && info->swapchainCount == 1 && info->pSwapchains &&
        info->pImageIndices && d->instance && d->instance->enabled) {
        pthread_mutex_lock(&d->lock);
        for (native_swapchain *sc = d->swapchains; sc; sc = sc->next) {
            if (sc->handle != info->pSwapchains[0]) continue;
            if (sc->copy_eligible && d->gpu_capable && !sc->gpu_attempted) {
                sc->gpu_attempted = 1;
                for (native_queue *q = d->queues; q; q = q->next) {
                    if (q->handle != queue) continue;
                    gfg_gpu_fg_create_info gi = {
                        .instance = d->instance->handle, .gipa = d->instance->gipa,
                        .physical = d->physical, .device = d->handle, .gdpa = d->gdpa,
                        .swapchain = sc->handle, .extent = sc->extent, .format = sc->format,
                        .present_mode = sc->present_mode, .queue = queue,
                        .family = q->family, .semaphore_fd = d->semaphore_fd,
                        .set_loader_data = d->set_loader_data};
                    sc->gpu = gfg_gpu_fg_create(&gi);
                    if (sc->gpu) sc->ids = native_ids_create(d, sc);
                    break;
                }
                if (!sc->gpu)
                    fprintf(stderr, "[gfg-native] GPU bridge not available; real-frame pass-through\n");
            } else if (!sc->gpu_attempted && !d->gpu_capable) {
                sc->gpu_attempted = 1;
                fprintf(stderr, "[gfg-native] GPU bridge not available (device lacks"
                        " external memory fd / timeline); real-frame pass-through\n");
            }
            gpu = sc->gpu;
            if (sc->ids) {
                ids.mode = sc->ids->mode;
                ids.assign = native_ids_assign;
                ids.user = sc->ids;
            }
            break;
        }
        pthread_mutex_unlock(&d->lock);
    }
    if (!want_gpu && info && info->swapchainCount == 1 && info->pSwapchains &&
        info->pImageIndices && flag && !strcmp(flag, "1") &&
        d->instance && d->instance->enabled) {
        pthread_mutex_lock(&d->lock);
        for (native_swapchain *sc = d->swapchains; sc; sc = sc->next) {
            if (sc->handle != info->pSwapchains[0]) continue;
            if (sc->copy_eligible && !sc->bridge_attempted) {
                sc->bridge_attempted = 1;
                for (native_queue *q = d->queues; q; q = q->next) {
                    if (q->handle != queue) continue;
                    sc->bridge = gfg_cpu_fg_create(d->instance->handle,
                        d->instance->gipa, d->physical, d->handle,
                        d->gdpa, sc->handle, sc->extent, sc->format,
                        queue, q->family);
                    break;
                }
                if (!sc->bridge)
                    fprintf(stderr,"[gfg-native] CPU bridge not available; real-frame pass-through\n");
            }
            bridge = sc->bridge;
            break;
        }
        pthread_mutex_unlock(&d->lock);
    }
    if (gpu) {
        path = "gpu";
        result = gfg_gpu_fg_present(gpu, queue, info, d->present, &ids);
    } else if (bridge) {
        path = "cpu";
        result = gfg_cpu_fg_present(bridge, info, d->present);
    } else {
        result = d->present(queue, info);
    }
#else
    result = d->present(queue, info);
#endif
    struct timespec present_end;
    clock_gettime(CLOCK_MONOTONIC, &present_end);
    const double present_us = 1e6 * (double)(present_end.tv_sec - present_start.tv_sec) +
        (double)(present_end.tv_nsec - present_start.tv_nsec) / 1e3;
    if (info && info->pSwapchains) {
        pthread_mutex_lock(&d->lock);
        for (uint32_t n = 0; n < info->swapchainCount; ++n)
            for (native_swapchain *sc = d->swapchains; sc; sc = sc->next)
                if (sc->handle == info->pSwapchains[n]) {
                    if (result == VK_SUCCESS || result == VK_SUBOPTIMAL_KHR) ++sc->presents;
                    sc->path = path;
                    if (sc->present_us && sc->present_samples < NATIVE_TIMING_CAP)
                        sc->present_us[sc->present_samples++] = present_us;
                    break;
                }
        pthread_mutex_unlock(&d->lock);
    }
    return result;
}

#ifdef GFG_NATIVE_WITH_TE
static native_present_ids *native_find_ids(native_device *d, VkSwapchainKHR swapchain) {
    native_present_ids *ids = NULL;
    pthread_mutex_lock(&d->lock);
    for (native_swapchain *sc = d->swapchains; sc; sc = sc->next)
        if (sc->handle == swapchain) { ids = sc->ids; break; }
    pthread_mutex_unlock(&d->lock);
    return ids;
}
static VKAPI_ATTR VkResult VKAPI_CALL
native_WaitForPresentKHR(VkDevice device, VkSwapchainKHR swapchain, uint64_t present_id,
                         uint64_t timeout) {
    native_device *d = find_device(dispatch_key(device));
    if (!d || !d->wait_present) return VK_ERROR_INITIALIZATION_FAILED;
    native_present_ids *ids = native_find_ids(d, swapchain);
    if (!ids || !present_id) return d->wait_present(device, swapchain, present_id, timeout);
    uint64_t layer_id = 0, remaining = 0;
    VkResult r = native_ids_translate(ids, present_id, timeout, &layer_id, &remaining);
    if (r != VK_SUCCESS) return r;
    return d->wait_present(device, swapchain, layer_id, remaining);
}
static VKAPI_ATTR VkResult VKAPI_CALL
native_WaitForPresent2KHR(VkDevice device, VkSwapchainKHR swapchain,
                          const VkPresentWait2InfoKHR *info) {
    native_device *d = find_device(dispatch_key(device));
    if (!d || !d->wait_present2) return VK_ERROR_INITIALIZATION_FAILED;
    native_present_ids *ids = native_find_ids(d, swapchain);
    if (!ids || !info || !info->presentId) return d->wait_present2(device, swapchain, info);
    uint64_t layer_id = 0, remaining = 0;
    VkResult r = native_ids_translate(ids, info->presentId, info->timeout, &layer_id, &remaining);
    if (r != VK_SUCCESS) return r;
    VkPresentWait2InfoKHR translated = *info; /* pNext kept */
    translated.presentId = layer_id;
    translated.timeout = remaining;
    return d->wait_present2(device, swapchain, &translated);
}
#endif

#define HOOK(name) if (!strcmp(symbol, "vk" #name)) return (PFN_vkVoidFunction)native_##name

static VKAPI_ATTR PFN_vkVoidFunction VKAPI_CALL
native_gdpa(VkDevice device, const char *symbol) {
    if (!symbol) return NULL;
    if (!strcmp(symbol, "vkGetDeviceProcAddr"))
        return (PFN_vkVoidFunction)native_gdpa;
    HOOK(DestroyDevice);
    if (!device) return NULL;
    native_device *d = find_device(dispatch_key(device));
    if (!d) return NULL;
    if (d->get_queue) HOOK(GetDeviceQueue);
    if (d->get_queue2) HOOK(GetDeviceQueue2);
    if (d->create_swapchain) HOOK(CreateSwapchainKHR);
    if (d->destroy_swapchain) HOOK(DestroySwapchainKHR);
    if (d->present) HOOK(QueuePresentKHR);
    if (d->acquire) HOOK(AcquireNextImageKHR);
    if (d->acquire2) HOOK(AcquireNextImage2KHR);
#ifdef GFG_NATIVE_WITH_TE
    if (d->wait_present) HOOK(WaitForPresentKHR);
    if (d->wait_present2) HOOK(WaitForPresent2KHR);
#endif
    return d->gdpa(device, symbol);
}

static VKAPI_ATTR PFN_vkVoidFunction VKAPI_CALL
native_gipa(VkInstance instance, const char *symbol) {
    if (!symbol) return NULL;
    if (!strcmp(symbol, "vkGetInstanceProcAddr"))
        return (PFN_vkVoidFunction)native_gipa;
    if (!strcmp(symbol, "vkGetDeviceProcAddr"))
        return (PFN_vkVoidFunction)native_gdpa;
    HOOK(CreateInstance);
    HOOK(DestroyInstance);
    HOOK(CreateDevice);
    if (!instance) return NULL;
    // Instance-level lookup of device commands must not bypass our layer.
    // Many Vulkan frameworks resolve WSI commands via vkGetInstanceProcAddr.
    if (!strcmp(symbol, "vkGetDeviceQueue"))
        return (PFN_vkVoidFunction)native_GetDeviceQueue;
    if (!strcmp(symbol, "vkGetDeviceQueue2"))
        return (PFN_vkVoidFunction)native_GetDeviceQueue2;
    if (!strcmp(symbol, "vkCreateSwapchainKHR"))
        return (PFN_vkVoidFunction)native_CreateSwapchainKHR;
    if (!strcmp(symbol, "vkDestroySwapchainKHR"))
        return (PFN_vkVoidFunction)native_DestroySwapchainKHR;
    if (!strcmp(symbol, "vkQueuePresentKHR"))
        return (PFN_vkVoidFunction)native_QueuePresentKHR;
    if (!strcmp(symbol, "vkAcquireNextImageKHR"))
        return (PFN_vkVoidFunction)native_AcquireNextImageKHR;
    if (!strcmp(symbol, "vkAcquireNextImage2KHR"))
        return (PFN_vkVoidFunction)native_AcquireNextImage2KHR;
#ifdef GFG_NATIVE_WITH_TE
    if (!strcmp(symbol, "vkWaitForPresentKHR"))
        return (PFN_vkVoidFunction)native_WaitForPresentKHR;
    if (!strcmp(symbol, "vkWaitForPresent2KHR"))
        return (PFN_vkVoidFunction)native_WaitForPresent2KHR;
#endif
    native_instance *i = find_instance(dispatch_key(instance));
    return i ? i->gipa(instance, symbol) : NULL;
}
#undef HOOK

#ifdef GFG_NATIVE_WITH_TE
/* Test hook: process-wide GPU bridge counters (see gpu_bridge.h). */
EXPORT void gfg_native_gpu_bridge_stats(gfg_gpu_stats *out) { gfg_gpu_fg_stats(out); }
#endif

EXPORT VKAPI_ATTR PFN_vkVoidFunction VKAPI_CALL
vkGetInstanceProcAddr(VkInstance instance, const char *name) {
    return native_gipa(instance, name);
}
EXPORT VKAPI_ATTR PFN_vkVoidFunction VKAPI_CALL
vkGetDeviceProcAddr(VkDevice device, const char *name) {
    return native_gdpa(device, name);
}
EXPORT VKAPI_ATTR VkResult VKAPI_CALL
vkNegotiateLoaderLayerInterfaceVersion(VkNegotiateLayerInterface *v) {
    if (!v || v->sType != LAYER_NEGOTIATE_INTERFACE_STRUCT ||
        v->loaderLayerInterfaceVersion < 2)
        return VK_ERROR_INITIALIZATION_FAILED;
    v->loaderLayerInterfaceVersion = 2;
    v->pfnGetInstanceProcAddr = native_gipa;
    v->pfnGetDeviceProcAddr = native_gdpa;
    v->pfnGetPhysicalDeviceProcAddr = NULL;
    return VK_SUCCESS;
}
