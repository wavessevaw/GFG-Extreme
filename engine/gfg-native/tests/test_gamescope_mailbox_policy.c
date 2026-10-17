/* Test-only Gamescope mailbox WSI to FIFO private-output policy. */
#include <stdio.h>
#include "../src/test_gamescope_swapchain_policy.h"
#include "../src/offscreen_source_pool.h"
#define REQUIRE(x) do {if(!(x)){fprintf(stderr,"GSF_MAILBOX_POLICY_FAIL line=%d\n",__LINE__);return 1;}}while(0)
int main(void) {
    const VkSwapchainCreateInfoKHR original={
        .sType=VK_STRUCTURE_TYPE_SWAPCHAIN_CREATE_INFO_KHR,
        .minImageCount=3,
        .imageFormat=VK_FORMAT_B8G8R8A8_UNORM,
        .imageColorSpace=VK_COLOR_SPACE_SRGB_NONLINEAR_KHR,
        .imageExtent={1280,800},
        .imageArrayLayers=1,
        .imageUsage=VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT |
                    VK_IMAGE_USAGE_TRANSFER_SRC_BIT |
                    VK_IMAGE_USAGE_TRANSFER_DST_BIT,
        .imageSharingMode=VK_SHARING_MODE_EXCLUSIVE,
        .presentMode=VK_PRESENT_MODE_MAILBOX_KHR
    };
    VkSwapchainCreateInfoKHR candidate={0};
    REQUIRE(gfg_offscreen_unsupported(&original));
    REQUIRE(!gfg_test_gamescope_normalize_fifo(&original,1,0,&candidate));
    REQUIRE(candidate.presentMode==VK_PRESENT_MODE_MAILBOX_KHR);
    REQUIRE(gfg_offscreen_unsupported(&candidate));
    REQUIRE(!gfg_test_gamescope_normalize_fifo(&original,0,1,&candidate));
    REQUIRE(gfg_offscreen_unsupported(&candidate));
    REQUIRE(gfg_test_gamescope_normalize_fifo(&original,1,1,&candidate));
    REQUIRE(candidate.presentMode==VK_PRESENT_MODE_FIFO_KHR);
    REQUIRE(candidate.imageUsage==original.imageUsage &&
            candidate.imageFormat==original.imageFormat &&
            candidate.minImageCount==original.minImageCount &&
            candidate.pNext==original.pNext);
    REQUIRE(gfg_offscreen_unsupported(&candidate)==NULL);
    /* Never bypass other safety guards or unknown Gamescope pNext. */
    candidate.flags=1;
    REQUIRE(gfg_offscreen_unsupported(&candidate));
    candidate.flags=0;
    candidate.imageFormat=VK_FORMAT_A2B10G10R10_UNORM_PACK32;
    REQUIRE(gfg_offscreen_unsupported(&candidate));
    candidate.imageFormat=original.imageFormat;
    candidate.imageColorSpace=VK_COLOR_SPACE_HDR10_ST2084_EXT;
    REQUIRE(gfg_offscreen_unsupported(&candidate));
    candidate.imageColorSpace=original.imageColorSpace;
    VkBaseInStructure unknown={.sType=(VkStructureType)0x7ffffffe,.pNext=NULL};
    candidate.pNext=&unknown;
    REQUIRE(gfg_offscreen_unsupported(&candidate));
    REQUIRE(!gfg_test_gamescope_normalize_fifo(NULL,1,1,&candidate));
    REQUIRE(!gfg_test_gamescope_normalize_fifo(&original,1,1,NULL));
    puts("GSF_GAMESCOPE_MAILBOX_POLICY only_gaming_live_adapter=1 FIFO_source=1 unsupported_pnext_hdr_flags_rejected=1 PASS");
    return 0;
}
