/* Test fixture: a stand-in for VK_LAYER_MAKO_render (frame generation) used to check layer order.
 *
 * Logs where it sits (stderr and, if set, appends to $MAKO_DUMMY_LOG) and, like a 2x frame
 * generator, turns every vkQueuePresentKHR into two presents down the chain.  A layer above it
 * sees N presents; a layer below it sees 2N.  Single instance/device is enough for the test. */
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <vulkan/vk_layer.h>
#include <vulkan/vulkan.h>

#define EXPORT __attribute__((visibility("default")))

static PFN_vkGetInstanceProcAddr next_gipa;
static PFN_vkGetDeviceProcAddr next_gdpa;
static PFN_vkDestroyInstance next_destroy_instance;
static PFN_vkDestroyDevice next_destroy_device;
static PFN_vkQueuePresentKHR next_present;

static void note(const char *what)
{
    fprintf(stderr, "[mako-dummy] %s\n", what);
    const char *path = getenv("MAKO_DUMMY_LOG");
    FILE *f = path && *path ? fopen(path, "a") : NULL;
    if (f) {
        fprintf(f, "VK_LAYER_MAKO_render %s\n", what);
        fclose(f);
    }
}

static VKAPI_ATTR VkResult VKAPI_CALL mako_CreateInstance(const VkInstanceCreateInfo *ci,
                                                           const VkAllocationCallbacks *a, VkInstance *out)
{
    VkLayerInstanceCreateInfo *l = (VkLayerInstanceCreateInfo *)ci->pNext;
    while (l && !(l->sType == VK_STRUCTURE_TYPE_LOADER_INSTANCE_CREATE_INFO && l->function == VK_LAYER_LINK_INFO))
        l = (VkLayerInstanceCreateInfo *)l->pNext;
    if (!l)
        return VK_ERROR_INITIALIZATION_FAILED;
    next_gipa = l->u.pLayerInfo->pfnNextGetInstanceProcAddr;
    l->u.pLayerInfo = l->u.pLayerInfo->pNext;
    note("enter vkCreateInstance");
    VkResult r = ((PFN_vkCreateInstance)next_gipa(VK_NULL_HANDLE, "vkCreateInstance"))(ci, a, out);
    note("leave vkCreateInstance");
    if (r == VK_SUCCESS)
        next_destroy_instance = (PFN_vkDestroyInstance)next_gipa(*out, "vkDestroyInstance");
    return r;
}

static VKAPI_ATTR void VKAPI_CALL mako_DestroyInstance(VkInstance i, const VkAllocationCallbacks *a)
{
    if (next_destroy_instance)
        next_destroy_instance(i, a);
}

static VKAPI_ATTR VkResult VKAPI_CALL mako_CreateDevice(VkPhysicalDevice p, const VkDeviceCreateInfo *ci,
                                                         const VkAllocationCallbacks *a, VkDevice *out)
{
    VkLayerDeviceCreateInfo *l = (VkLayerDeviceCreateInfo *)ci->pNext;
    while (l && !(l->sType == VK_STRUCTURE_TYPE_LOADER_DEVICE_CREATE_INFO && l->function == VK_LAYER_LINK_INFO))
        l = (VkLayerDeviceCreateInfo *)l->pNext;
    if (!l)
        return VK_ERROR_INITIALIZATION_FAILED;
    PFN_vkGetInstanceProcAddr gipa = l->u.pLayerInfo->pfnNextGetInstanceProcAddr;
    next_gdpa = l->u.pLayerInfo->pfnNextGetDeviceProcAddr;
    l->u.pLayerInfo = l->u.pLayerInfo->pNext;
    VkResult r = ((PFN_vkCreateDevice)gipa(VK_NULL_HANDLE, "vkCreateDevice"))(p, ci, a, out);
    if (r == VK_SUCCESS) {
        next_destroy_device = (PFN_vkDestroyDevice)next_gdpa(*out, "vkDestroyDevice");
        next_present = (PFN_vkQueuePresentKHR)next_gdpa(*out, "vkQueuePresentKHR");
    }
    return r;
}

static VKAPI_ATTR void VKAPI_CALL mako_DestroyDevice(VkDevice d, const VkAllocationCallbacks *a)
{
    if (next_destroy_device)
        next_destroy_device(d, a);
}

static int presents;

static VKAPI_ATTR VkResult VKAPI_CALL mako_QueuePresentKHR(VkQueue q, const VkPresentInfoKHR *info)
{
    if (presents++ == 0)
        note("vkQueuePresentKHR (2 presents down per call)");
    VkResult r = next_present(q, info);   /* "generated" frame */
    if (r != VK_SUCCESS && r != VK_SUBOPTIMAL_KHR)
        return r;
    return next_present(q, info);         /* real frame */
}

static VKAPI_ATTR PFN_vkVoidFunction VKAPI_CALL mako_GetDeviceProcAddr(VkDevice d, const char *n);

static VKAPI_ATTR PFN_vkVoidFunction VKAPI_CALL mako_GetInstanceProcAddr(VkInstance i, const char *n)
{
    if (!strcmp(n, "vkGetInstanceProcAddr")) return (PFN_vkVoidFunction)mako_GetInstanceProcAddr;
    if (!strcmp(n, "vkCreateInstance")) return (PFN_vkVoidFunction)mako_CreateInstance;
    if (!strcmp(n, "vkDestroyInstance")) return (PFN_vkVoidFunction)mako_DestroyInstance;
    if (!strcmp(n, "vkCreateDevice")) return (PFN_vkVoidFunction)mako_CreateDevice;
    if (!strcmp(n, "vkGetDeviceProcAddr")) return (PFN_vkVoidFunction)mako_GetDeviceProcAddr;
    return i && next_gipa ? next_gipa(i, n) : NULL;
}

static VKAPI_ATTR PFN_vkVoidFunction VKAPI_CALL mako_GetDeviceProcAddr(VkDevice d, const char *n)
{
    if (!strcmp(n, "vkGetDeviceProcAddr")) return (PFN_vkVoidFunction)mako_GetDeviceProcAddr;
    if (!strcmp(n, "vkDestroyDevice")) return (PFN_vkVoidFunction)mako_DestroyDevice;
    if (!strcmp(n, "vkQueuePresentKHR") && next_present) return (PFN_vkVoidFunction)mako_QueuePresentKHR;
    return d && next_gdpa ? next_gdpa(d, n) : NULL;
}

EXPORT VKAPI_ATTR VkResult VKAPI_CALL vkNegotiateLoaderLayerInterfaceVersion(VkNegotiateLayerInterface *v)
{
    if (!v || v->loaderLayerInterfaceVersion < 2)
        return VK_ERROR_INITIALIZATION_FAILED;
    v->loaderLayerInterfaceVersion = 2;
    v->pfnGetInstanceProcAddr = mako_GetInstanceProcAddr;
    v->pfnGetDeviceProcAddr = mako_GetDeviceProcAddr;
    v->pfnGetPhysicalDeviceProcAddr = NULL;
    return VK_SUCCESS;
}
