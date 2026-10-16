/* SPDX-License-Identifier: GPL-3.0-or-later
 * Hardware-independent check for the Steam Deck's actual swapchain request.
 * NEVER send present-id2 flags to an ICD lacking the corresponding extension.
 * The test exercises our eligibility filter only, not a fabricated surface.
 */
#define _GNU_SOURCE /* layer.c uses clock_gettime; must precede the first libc header */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "../src/layer.c"

int main(void) {
    VkSwapchainCreateInfoKHR ci = {
        .sType = VK_STRUCTURE_TYPE_SWAPCHAIN_CREATE_INFO_KHR,
        .flags = VK_SWAPCHAIN_CREATE_PRESENT_ID_2_BIT_KHR |
                 VK_SWAPCHAIN_CREATE_PRESENT_WAIT_2_BIT_KHR,
        .imageFormat = VK_FORMAT_B8G8R8A8_UNORM,
        .imageExtent = {1280, 800},
        .imageArrayLayers = 1,
        .imageUsage = 0x1b,
        .imageSharingMode = VK_SHARING_MODE_EXCLUSIVE,
        .presentMode = VK_PRESENT_MODE_FIFO_KHR,
    };
    assert(ci.flags == 0xc0);
    assert((int)ci.imageFormat == 44);
    assert(native_ineligible_reason(&ci) == NULL);
    assert(native_copy_usage_ready(ci.imageUsage));
    assert(native_can_add_two_images(3, 0));
    assert(native_can_add_two_images(3, 5));
    assert(!native_can_add_two_images(3, 4));
    assert(!native_can_add_two_images(5, 4));
    puts("GFG native: actual Steam Deck 0xc0/44/0x1b swapchain eligible PASS");
    ci.flags = VK_SWAPCHAIN_CREATE_PROTECTED_BIT_KHR;
    assert(!strcmp(native_ineligible_reason(&ci), "unsupported-swapchain-flags"));
    ci.flags = VK_SWAPCHAIN_CREATE_MUTABLE_FORMAT_BIT_KHR;
    assert(!strcmp(native_ineligible_reason(&ci), "unsupported-swapchain-flags"));
    ci.flags = 0x1000;
    assert(!strcmp(native_ineligible_reason(&ci), "unsupported-swapchain-flags"));
    ci.flags = VK_SWAPCHAIN_CREATE_PRESENT_WAIT_2_BIT_KHR;
    assert(native_ineligible_reason(&ci) == NULL);
    ci.flags = VK_SWAPCHAIN_CREATE_PRESENT_ID_2_BIT_KHR;
    assert(native_ineligible_reason(&ci) == NULL);
    ci.flags = 0;
    assert(native_ineligible_reason(&ci) == NULL);
    ci.presentMode = VK_PRESENT_MODE_MAILBOX_KHR;
    assert(!strcmp(native_ineligible_reason(&ci), "non-fifo-present-mode"));
    ci.presentMode = VK_PRESENT_MODE_FIFO_RELAXED_KHR;
    assert(!strcmp(native_ineligible_reason(&ci), "non-fifo-present-mode"));
    ci.presentMode = VK_PRESENT_MODE_FIFO_KHR;
    ci.imageUsage = VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT;
    assert(!native_copy_usage_ready(ci.imageUsage));
    ci.imageSharingMode = VK_SHARING_MODE_CONCURRENT;
    assert(!strcmp(native_ineligible_reason(&ci), "sharing-mode"));
    puts("GFG native: present-extension mask and protection refusal PASS");
    ci.imageSharingMode=VK_SHARING_MODE_EXCLUSIVE;
    ci.imageFormat=VK_FORMAT_A2B10G10R10_UNORM_PACK32;
    setenv("GFG_NATIVE_GPU_BRIDGE","1",1);
    assert(native_ineligible_reason(&ci)==NULL);
    ci.imageColorSpace=VK_COLOR_SPACE_HDR10_ST2084_EXT;
    assert(native_ineligible_reason(&ci)==NULL);
    ci.imageColorSpace=VK_COLOR_SPACE_HDR10_HLG_EXT;
    assert(!strcmp(native_ineligible_reason(&ci),"unsupported-color-space"));
    ci.imageColorSpace=VK_COLOR_SPACE_HDR10_ST2084_EXT;ci.imageFormat=VK_FORMAT_B8G8R8A8_UNORM;
    assert(!strcmp(native_ineligible_reason(&ci),"unsupported-pq-format"));
    ci.imageColorSpace=VK_COLOR_SPACE_SRGB_NONLINEAR_KHR;ci.imageFormat=VK_FORMAT_A2B10G10R10_UNORM_PACK32;
    VkPresentModeKHR mailbox=VK_PRESENT_MODE_MAILBOX_KHR;
    const VkSwapchainPresentModesCreateInfoEXT modes={.sType=VK_STRUCTURE_TYPE_SWAPCHAIN_PRESENT_MODES_CREATE_INFO_EXT,
        .presentModeCount=1,.pPresentModes=&mailbox};
    const VkImageFormatListCreateInfo formats={.sType=VK_STRUCTURE_TYPE_IMAGE_FORMAT_LIST_CREATE_INFO,.pNext=&modes};
    ci.pNext=&formats;ci.presentMode=mailbox;
    VkSwapchainCreateInfoKHR effective=ci;gfg_create_chain copy;
    assert(gfg_create_fifo(&copy,&effective));
    assert(ci.pNext==&formats && formats.pNext==&modes && modes.pPresentModes[0]==mailbox);
    const VkImageFormatListCreateInfo *f=effective.pNext;
    const VkSwapchainPresentModesCreateInfoEXT *m=f->pNext;
    assert(effective.presentMode==VK_PRESENT_MODE_FIFO_KHR && f!=&formats && m!=&modes);
    assert(m->presentModeCount==1 && m->pPresentModes[0]==VK_PRESENT_MODE_FIFO_KHR);
    VkBaseInStructure unknown={.sType=(VkStructureType)1999999999,.pNext=(const void*)&modes};
    effective=ci;effective.pNext=&unknown;
    assert(!gfg_create_fifo(&copy,&effective));
    assert(effective.pNext==&unknown && effective.presentMode==mailbox);
    unsetenv("GFG_NATIVE_GPU_BRIDGE");
    puts("GFG native: HDR10 eligibility and immutable FIFO create-mode prefix PASS");
    return 0;
}
