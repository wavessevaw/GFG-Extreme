/* SPDX-License-Identifier: GPL-3.0-or-later
 * Test-only SteamOS Gamescope WSI present-mode bridge.
 *
 * Gamescope may rewrite an app FIFO request to MAILBOX before our explicit
 * Vulkan layer sees the create. Virtual source image retirement and the
 * independent output owner require the FIFO schedule in this experiment.
 * Never permit this translation outside the isolated opt-in live test.
 * This does NOT prove the compositor's physical OLED scanout timing.
 */
#ifndef GFG_TEST_GAMESCOPE_SWAPCHAIN_POLICY_H
#define GFG_TEST_GAMESCOPE_SWAPCHAIN_POLICY_H
#include <vulkan/vulkan.h>
static inline int gfg_test_gamescope_normalize_fifo(
        const VkSwapchainCreateInfoKHR *original,
        int live_test,int gaming_mode,
        VkSwapchainCreateInfoKHR *result) {
    if(!original || !result)return 0;
    *result=*original;
    if(!live_test || !gaming_mode ||
       original->presentMode!=VK_PRESENT_MODE_MAILBOX_KHR)
        return 0;
    result->presentMode=VK_PRESENT_MODE_FIFO_KHR;
    return 1;
}
#endif
