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
    return 0;
}
