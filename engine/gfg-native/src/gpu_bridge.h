/* SPDX-License-Identifier: GPL-3.0-or-later */
#ifndef GFG_GPU_BRIDGE_H
#define GFG_GPU_BRIDGE_H
#include <vulkan/vulkan.h>
#include <vulkan/vk_layer.h>
typedef struct gfg_gpu_fg gfg_gpu_fg;
gfg_gpu_fg *gfg_gpu_fg_create(VkInstance instance, PFN_vkGetInstanceProcAddr gipa, VkPhysicalDevice physical,
    VkDevice device, PFN_vkGetDeviceProcAddr gdpa, VkSwapchainKHR swapchain,
    VkExtent2D extent, VkFormat format, VkQueue queue, uint32_t family,
    PFN_vkSetDeviceLoaderData set_loader_data);
VkResult gfg_gpu_fg_present(gfg_gpu_fg *fg, VkQueue queue, const VkPresentInfoKHR *original,
    PFN_vkQueuePresentKHR next_present);
/* Reset temporal history when an application presentation bypasses capture. */
void gfg_gpu_fg_reset(gfg_gpu_fg *fg);
void gfg_gpu_fg_destroy(gfg_gpu_fg *fg);
#endif
