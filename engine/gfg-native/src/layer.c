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
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <vulkan/vulkan.h>
#include <vulkan/vk_layer.h>
#ifdef GFG_NATIVE_WITH_TE
#include "cpu_bridge.h"
#endif

#define EXPORT __attribute__((visibility("default")))

typedef struct native_instance {
    struct native_instance *next;
    void *key;
    VkInstance handle;
    PFN_vkGetInstanceProcAddr gipa;
    PFN_vkDestroyInstance destroy;
    PFN_vkGetPhysicalDeviceSurfaceCapabilitiesKHR surface_caps;
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
#endif
    int copy_eligible; /* enabled transfer usage only; never means captured */
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
    link->u.pLayerInfo = link->u.pLayerInfo->pNext;
    PFN_vkCreateDevice next = (PFN_vkCreateDevice)
        gipa(VK_NULL_HANDLE, "vkCreateDevice");
    if (!next) return VK_ERROR_INITIALIZATION_FAILED;
    VkResult result = next(phys, ci, alloc, out);
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
#ifdef GFG_NATIVE_WITH_TE
        if (sc->bridge) gfg_cpu_fg_destroy(sc->bridge);
#endif
        free(sc->owned);
        free(sc);
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

static int eligible_shape(const VkSwapchainCreateInfoKHR *ci) {
    if (ci->flags || ci->imageArrayLayers != 1 ||
        ci->imageSharingMode != VK_SHARING_MODE_EXCLUSIVE ||
        !ci->imageExtent.width || !ci->imageExtent.height)
        return 0;
    return ci->imageFormat == VK_FORMAT_R8G8B8A8_UNORM ||
           ci->imageFormat == VK_FORMAT_B8G8R8A8_UNORM;
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
    VkSwapchainCreateInfoKHR extended = *ci;
    if (d->instance && d->instance->enabled && eligible_shape(ci) &&
        d->instance->surface_caps) {
        VkSurfaceCapabilitiesKHR caps = {0};
        VkResult cr = d->instance->surface_caps(d->physical, ci->surface, &caps);
        const VkImageUsageFlags wanted =
            VK_IMAGE_USAGE_TRANSFER_SRC_BIT | VK_IMAGE_USAGE_TRANSFER_DST_BIT;
        if (cr == VK_SUCCESS && (caps.supportedUsageFlags & wanted) == wanted) {
            extended.imageUsage |= wanted;
            candidate = 1;
        }
    }
    VkResult result = d->create_swapchain(device, candidate ? &extended : ci,
                                           alloc, out);
    if (result != VK_SUCCESS && candidate) {
        // Negotiation must never stop a game from creating its original surface.
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
        fprintf(stderr, "[gfg-native] swapchain %ux%u candidate=%d output=real-only\n",
            sc->extent.width, sc->extent.height, sc->copy_eligible);
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
#ifdef GFG_NATIVE_WITH_TE
            if (old->bridge) gfg_cpu_fg_destroy(old->bridge);
#endif
            free(old->owned);
            free(old);
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
#ifdef GFG_NATIVE_WITH_TE
    gfg_cpu_fg *bridge = NULL;
    const char *flag = getenv("GFG_NATIVE_CPU_BRIDGE");
    if (info && info->swapchainCount == 1 && info->pSwapchains &&
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
    result = bridge ? gfg_cpu_fg_present(bridge, info, d->present) :
                      d->present(queue, info);
#else
    result = d->present(queue, info);
#endif
    if ((result == VK_SUCCESS || result == VK_SUBOPTIMAL_KHR) && info) {
        pthread_mutex_lock(&d->lock);
        for (uint32_t n = 0; n < info->swapchainCount; ++n)
            for (native_swapchain *sc = d->swapchains; sc; sc = sc->next)
                if (sc->handle == info->pSwapchains[n]) {
                    ++sc->presents; break;
                }
        pthread_mutex_unlock(&d->lock);
    }
    return result;
}

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
    native_instance *i = find_instance(dispatch_key(instance));
    return i ? i->gipa(instance, symbol) : NULL;
}
#undef HOOK

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
