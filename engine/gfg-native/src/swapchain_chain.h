/* SPDX-License-Identifier: GPL-3.0-or-later
 * Private create-chain prefix for an explicitly requested FIFO override.
 * Arrays remain borrowed only during synchronous vkCreateSwapchainKHR.
 */
#ifndef GFG_SWAPCHAIN_CHAIN_H
#define GFG_SWAPCHAIN_CHAIN_H
#include <string.h>
#include <vulkan/vulkan.h>
typedef union {
    VkBaseOutStructure base;
    VkSwapchainPresentModesCreateInfoEXT modes;
    VkImageFormatListCreateInfo formats;
    VkDeviceGroupSwapchainCreateInfoKHR group;
    VkSwapchainPresentScalingCreateInfoEXT scaling;
    VkImageCompressionControlEXT compression;
    VkSwapchainPresentBarrierCreateInfoNV barrier;
    VkSwapchainCounterCreateInfoEXT counter;
} gfg_create_node;
typedef struct { gfg_create_node nodes[16]; VkPresentModeKHR fifo; } gfg_create_chain;
/* Preserve an unknown suffix verbatim. Never guess the size of an unknown
 * prefix node that would have to be relinked to the rewritten mode list. */
static inline int gfg_create_fifo(gfg_create_chain *copy, VkSwapchainCreateInfoKHR *ci) {
    const VkBaseInStructure *n=ci->pNext; unsigned at=0, target=16;
    for(;n && at<16;n=n->pNext,++at)
        if(n->sType==VK_STRUCTURE_TYPE_SWAPCHAIN_PRESENT_MODES_CREATE_INFO_EXT) {target=at;break;}
    if(n && at==16) return 0;
    copy->fifo=VK_PRESENT_MODE_FIFO_KHR;
    if(target!=16) {
        n=ci->pNext;
        for(at=0;at<=target;++at,n=n->pNext) {
            size_t size;
            switch(n->sType) {
#define NODE(type,structure) case type:size=sizeof(structure);break
            NODE(VK_STRUCTURE_TYPE_SWAPCHAIN_PRESENT_MODES_CREATE_INFO_EXT,VkSwapchainPresentModesCreateInfoEXT);
            NODE(VK_STRUCTURE_TYPE_IMAGE_FORMAT_LIST_CREATE_INFO,VkImageFormatListCreateInfo);
            NODE(VK_STRUCTURE_TYPE_DEVICE_GROUP_SWAPCHAIN_CREATE_INFO_KHR,VkDeviceGroupSwapchainCreateInfoKHR);
            NODE(VK_STRUCTURE_TYPE_SWAPCHAIN_PRESENT_SCALING_CREATE_INFO_EXT,VkSwapchainPresentScalingCreateInfoEXT);
            NODE(VK_STRUCTURE_TYPE_IMAGE_COMPRESSION_CONTROL_EXT,VkImageCompressionControlEXT);
            NODE(VK_STRUCTURE_TYPE_SWAPCHAIN_PRESENT_BARRIER_CREATE_INFO_NV,VkSwapchainPresentBarrierCreateInfoNV);
            NODE(VK_STRUCTURE_TYPE_SWAPCHAIN_COUNTER_CREATE_INFO_EXT,VkSwapchainCounterCreateInfoEXT);
#undef NODE
            default:return 0;
            }
            memcpy(&copy->nodes[at],n,size);
            if(at) copy->nodes[at-1].base.pNext=&copy->nodes[at].base;
        }
        copy->nodes[target].modes.presentModeCount=1;
        copy->nodes[target].modes.pPresentModes=&copy->fifo;
        ci->pNext=&copy->nodes[0];
    }
    ci->presentMode=VK_PRESENT_MODE_FIFO_KHR;
    return 1;
}
#endif
