/* SPDX-License-Identifier: GPL-3.0-or-later
 * Loader-installed virtual WSI: GPU render -> layer capture worker -> real
 * compositor output -> X11 pixel check. Synthetic colors only, not FG.
 */
#define _POSIX_C_SOURCE 200809L
#ifndef VK_USE_PLATFORM_XCB_KHR
#define VK_USE_PLATFORM_XCB_KHR
#endif
#include <vulkan/vulkan.h>
#include <vulkan/vulkan_xcb.h>
#include "../src/offscreen_source_pool.h"
#include "x11_output_probe.h"
#include <xcb/xcb.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

#define REQUIRE(x) do { if (!(x)) { \
    fprintf(stderr,"GSF loader probe assertion: %s line %d\\n",#x,__LINE__); \
    return 1; } } while(0)
#define TRY(x) do { VkResult r_=(x); if(r_!=VK_SUCCESS) { \
    fprintf(stderr,"GSF loader probe Vulkan error %s: %d line %d\\n",#x,r_,__LINE__); \
    return 1; } } while(0)

int main(void) {
    REQUIRE(getenv("GFG_NATIVE_TEST_LOADER_LIVE_OUTPUT"));
    REQUIRE(getenv("GFG_NATIVE_TEST_PROXY_CREATE"));
    xcb_connection_t *x=xcb_connect(NULL,NULL);
    REQUIRE(x && !xcb_connection_has_error(x));
    const xcb_setup_t *setup=xcb_get_setup(x);
    xcb_screen_t *screen=xcb_setup_roots_iterator(setup).data;
    REQUIRE(screen);
    const xcb_window_t window=xcb_generate_id(x);
    const uint32_t attributes[1]={screen->black_pixel};
    xcb_create_window(x,XCB_COPY_FROM_PARENT,window,screen->root,
        0,0,96,64,0,XCB_WINDOW_CLASS_INPUT_OUTPUT,
        screen->root_visual,XCB_CW_BACK_PIXEL,attributes);
    xcb_map_window(x,window);
    REQUIRE(xcb_flush(x)>0);

    const char *instance_extensions[]={"VK_KHR_surface","VK_KHR_xcb_surface"};
    VkApplicationInfo app={.sType=VK_STRUCTURE_TYPE_APPLICATION_INFO,
        .pApplicationName="gsf-loader-proxy-live-output",
        .pEngineName="gfg-output-loader-probe",.apiVersion=VK_API_VERSION_1_2};
    VkInstanceCreateInfo ic={.sType=VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO,
        .pApplicationInfo=&app,.enabledExtensionCount=2,
        .ppEnabledExtensionNames=instance_extensions};
    VkInstance instance=VK_NULL_HANDLE;
    TRY(vkCreateInstance(&ic,NULL,&instance));
    VkXcbSurfaceCreateInfoKHR xc={.sType=VK_STRUCTURE_TYPE_XCB_SURFACE_CREATE_INFO_KHR,
        .connection=x,.window=window};
    VkSurfaceKHR surface=VK_NULL_HANDLE;
    TRY(vkCreateXcbSurfaceKHR(instance,&xc,NULL,&surface));

    uint32_t phys_count=0;TRY(vkEnumeratePhysicalDevices(instance,&phys_count,NULL));
    REQUIRE(phys_count && phys_count<64);
    VkPhysicalDevice *physical_list=calloc(phys_count,sizeof(*physical_list));
    REQUIRE(physical_list);
    TRY(vkEnumeratePhysicalDevices(instance,&phys_count,physical_list));
    VkPhysicalDevice physical=VK_NULL_HANDLE;
    uint32_t family=UINT32_MAX;
    for(uint32_t i=0;i<phys_count && !physical;i++) {
        uint32_t families=0;
        vkGetPhysicalDeviceQueueFamilyProperties(physical_list[i],&families,NULL);
        VkQueueFamilyProperties *props=calloc(families,sizeof(*props));
        REQUIRE(props);
        vkGetPhysicalDeviceQueueFamilyProperties(physical_list[i],&families,props);
        for(uint32_t j=0;j<families;j++) {
            VkBool32 supported=VK_FALSE;
            if(props[j].queueFlags&VK_QUEUE_GRAPHICS_BIT)
                TRY(vkGetPhysicalDeviceSurfaceSupportKHR(physical_list[i],j,
                                                         surface,&supported));
            if(supported){physical=physical_list[i];family=j;break;}
        }
        free(props);
    }
    free(physical_list);
    REQUIRE(physical && family!=UINT32_MAX);
    const float priority=1.0f;
    VkDeviceQueueCreateInfo queue_info={.sType=VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO,
        .queueFamilyIndex=family,.queueCount=1,.pQueuePriorities=&priority};
    const char *device_extensions[]={"VK_KHR_swapchain"};
    VkDeviceCreateInfo dc={.sType=VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO,
        .queueCreateInfoCount=1,.pQueueCreateInfos=&queue_info,
        .enabledExtensionCount=1,.ppEnabledExtensionNames=device_extensions};
    VkDevice device=VK_NULL_HANDLE;
    TRY(vkCreateDevice(physical,&dc,NULL,&device));
    VkSurfaceCapabilitiesKHR caps={0};
    TRY(vkGetPhysicalDeviceSurfaceCapabilitiesKHR(physical,surface,&caps));
    const VkImageUsageFlags needed=VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT |
        VK_IMAGE_USAGE_TRANSFER_SRC_BIT | VK_IMAGE_USAGE_TRANSFER_DST_BIT;
    REQUIRE((caps.supportedUsageFlags & needed)==needed);
    uint32_t nformat=0;TRY(vkGetPhysicalDeviceSurfaceFormatsKHR(physical,surface,&nformat,NULL));
    REQUIRE(nformat && nformat<512);
    VkSurfaceFormatKHR *formats=calloc(nformat,sizeof(*formats));
    REQUIRE(formats);
    TRY(vkGetPhysicalDeviceSurfaceFormatsKHR(physical,surface,&nformat,formats));
    VkSurfaceFormatKHR fmt={0};
    for(uint32_t i=0;i<nformat;i++)
        if(formats[i].format==VK_FORMAT_B8G8R8A8_UNORM &&
           formats[i].colorSpace==VK_COLOR_SPACE_SRGB_NONLINEAR_KHR) {
            fmt=formats[i];break;
        }
    free(formats);
    REQUIRE(fmt.format==VK_FORMAT_B8G8R8A8_UNORM);
    uint32_t count=caps.minImageCount<2?2:caps.minImageCount;
    REQUIRE(count<=GFG_OFFSCREEN_MAX_IMAGES);
    REQUIRE(!caps.maxImageCount || count<=caps.maxImageCount);
    VkExtent2D extent=caps.currentExtent;
    if(extent.width==UINT32_MAX)extent=(VkExtent2D){96,64};
    VkSwapchainCreateInfoKHR ci={.sType=VK_STRUCTURE_TYPE_SWAPCHAIN_CREATE_INFO_KHR,
        .surface=surface,.minImageCount=count,
        .imageFormat=fmt.format,.imageColorSpace=fmt.colorSpace,
        .imageExtent=extent,.imageArrayLayers=1,.imageUsage=needed,
        .imageSharingMode=VK_SHARING_MODE_EXCLUSIVE,
        .preTransform=caps.currentTransform,
        .compositeAlpha=VK_COMPOSITE_ALPHA_OPAQUE_BIT_KHR,
        .presentMode=VK_PRESENT_MODE_FIFO_KHR,.clipped=VK_TRUE};
    if(!(caps.supportedCompositeAlpha&VK_COMPOSITE_ALPHA_OPAQUE_BIT_KHR))
        for(unsigned bit=1;bit<=8;bit*=2)
            if(caps.supportedCompositeAlpha&bit) {
                ci.compositeAlpha=(VkCompositeAlphaFlagBitsKHR)bit;break;
            }

    VkSwapchainKHR virtual_handle=VK_NULL_HANDLE;
    TRY(vkCreateSwapchainKHR(device,&ci,NULL,&virtual_handle));
    REQUIRE(virtual_handle);
    uint32_t images_count=0;
    TRY(vkGetSwapchainImagesKHR(device,virtual_handle,&images_count,NULL));
    REQUIRE(images_count==count);
    VkImage images[GFG_OFFSCREEN_MAX_IMAGES]={0};
    TRY(vkGetSwapchainImagesKHR(device,virtual_handle,&images_count,images));
    for(uint32_t i=0;i<images_count;i++) {
        REQUIRE(images[i]!=VK_NULL_HANDLE);
        for(uint32_t j=0;j<i;j++)REQUIRE(images[i]!=images[j]);
    }
    /* Vulkan app uses the loader and its normal vk* dispatch. No layer
     * device registration or injected callbacks from the test executable. */
    VkQueue queue=VK_NULL_HANDLE;
    vkGetDeviceQueue(device,family,0,&queue);
    REQUIRE(queue);
    VkCommandPool pool=VK_NULL_HANDLE;
    const VkCommandPoolCreateInfo pool_info={
        .sType=VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO,
        .flags=VK_COMMAND_POOL_CREATE_RESET_COMMAND_BUFFER_BIT,
        .queueFamilyIndex=family};
    TRY(vkCreateCommandPool(device,&pool_info,NULL,&pool));
    const VkCommandBufferAllocateInfo cb_info={
        .sType=VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO,
        .commandPool=pool,.level=VK_COMMAND_BUFFER_LEVEL_PRIMARY,
        .commandBufferCount=1};
    VkCommandBuffer cmd=VK_NULL_HANDLE;
    TRY(vkAllocateCommandBuffers(device,&cb_info,&cmd));
    const VkSemaphoreCreateInfo sem_info={.sType=VK_STRUCTURE_TYPE_SEMAPHORE_CREATE_INFO};
    VkSemaphore image_ready=VK_NULL_HANDLE,render_done=VK_NULL_HANDLE;
    TRY(vkCreateSemaphore(device,&sem_info,NULL,&image_ready));
    TRY(vkCreateSemaphore(device,&sem_info,NULL,&render_done));
    const VkFenceCreateInfo fc={
        .sType=VK_STRUCTURE_TYPE_FENCE_CREATE_INFO,
        .flags=VK_FENCE_CREATE_SIGNALED_BIT};
    VkFence rendering=VK_NULL_HANDLE;
    TRY(vkCreateFence(device,&fc,NULL,&rendering));
    unsigned char seen[GFG_OFFSCREEN_MAX_IMAGES]={0};
    const int interleave=getenv("GFG_NATIVE_TEST_OUTPUT_INTERLEAVE")!=NULL;
    uint32_t visible=0, intermediate_visible=0, output_visible=0;
    int last_level=-1;
    for(uint32_t frame=1;frame<=8;frame++) {
        uint32_t index=UINT32_MAX;
        TRY(vkAcquireNextImageKHR(device,virtual_handle,UINT64_MAX,
                                  image_ready,VK_NULL_HANDLE,&index));
        REQUIRE(index<images_count);
        TRY(vkWaitForFences(device,1,&rendering,VK_TRUE,UINT64_MAX));
        TRY(vkResetCommandBuffer(cmd,0));
        const VkCommandBufferBeginInfo begin={
            .sType=VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO};
        TRY(vkBeginCommandBuffer(cmd,&begin));
        /* The layer rewrites PRESENT_SRC_KHR to TRANSFER_SRC_OPTIMAL on
         * virtual images ONLY. The app draws a different color per frame. */
        VkImageMemoryBarrier pre={
            .sType=VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER,
            .srcAccessMask=seen[index]?VK_ACCESS_TRANSFER_READ_BIT:0,
            .dstAccessMask=VK_ACCESS_TRANSFER_WRITE_BIT,
            .oldLayout=seen[index]?VK_IMAGE_LAYOUT_PRESENT_SRC_KHR:
                                   VK_IMAGE_LAYOUT_UNDEFINED,
            .newLayout=VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL,
            .srcQueueFamilyIndex=VK_QUEUE_FAMILY_IGNORED,
            .dstQueueFamilyIndex=VK_QUEUE_FAMILY_IGNORED,
            .image=images[index],
            .subresourceRange={VK_IMAGE_ASPECT_COLOR_BIT,0,1,0,1}};
        vkCmdPipelineBarrier(cmd,seen[index]?
            VK_PIPELINE_STAGE_TRANSFER_BIT:VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT,
            VK_PIPELINE_STAGE_TRANSFER_BIT,0,0,NULL,0,NULL,1,&pre);
        const float level=0.15f+0.11f*(float)(frame%5u);
        const VkClearColorValue grey={.float32={level,level,level,1}};
        const VkImageSubresourceRange range={VK_IMAGE_ASPECT_COLOR_BIT,0,1,0,1};
        vkCmdClearColorImage(cmd,images[index],VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL,
                             &grey,1,&range);
        VkImageMemoryBarrier post=pre;
        post.srcAccessMask=VK_ACCESS_TRANSFER_WRITE_BIT;
        post.dstAccessMask=VK_ACCESS_TRANSFER_READ_BIT;
        post.oldLayout=VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL;
        post.newLayout=VK_IMAGE_LAYOUT_PRESENT_SRC_KHR;
        vkCmdPipelineBarrier(cmd,VK_PIPELINE_STAGE_TRANSFER_BIT,
            VK_PIPELINE_STAGE_TRANSFER_BIT,0,0,NULL,0,NULL,1,&post);
        TRY(vkEndCommandBuffer(cmd));
        TRY(vkResetFences(device,1,&rendering));
        const VkPipelineStageFlags stage=VK_PIPELINE_STAGE_TRANSFER_BIT;
        const VkSubmitInfo submit={
            .sType=VK_STRUCTURE_TYPE_SUBMIT_INFO,
            .waitSemaphoreCount=1,.pWaitSemaphores=&image_ready,
            .pWaitDstStageMask=&stage,.commandBufferCount=1,
            .pCommandBuffers=&cmd,
            .signalSemaphoreCount=1,.pSignalSemaphores=&render_done};
        TRY(vkQueueSubmit(queue,1,&submit,rendering));
        VkResult single=VK_ERROR_UNKNOWN;
        const VkPresentInfoKHR present={
            .sType=VK_STRUCTURE_TYPE_PRESENT_INFO_KHR,
            .waitSemaphoreCount=1,.pWaitSemaphores=&render_done,
            .swapchainCount=1,.pSwapchains=&virtual_handle,
            .pImageIndices=&index,.pResults=&single};
        TRY(vkQueuePresentKHR(queue,&present));
        REQUIRE(single==VK_SUCCESS);
        const int expected=(int)(level*255.f+0.5f);
        /* X11 must expose the inserted A|B frame before the real B.
         * The synthetic GPU composite is unique: left pixel from A,
         * right pixel from B. A mere duplicate present cannot pass. */
        if(interleave && frame>1) {
            REQUIRE(last_level>=0 && last_level!=expected);
            uint64_t middle_latency=0;
            REQUIRE(gfg_x11_wait_visible_pair(x,window,extent.width,extent.height,
                    last_level,expected,1500000000ull,&middle_latency));
            ++intermediate_visible;
            ++output_visible;
            fprintf(stderr,"GSF_LOADER_SPLIT_APP frame=%u left=%d right=%d x11_visible=1 latency_us=%llu\n",
                    frame,last_level,expected,(unsigned long long)(middle_latency/1000));
        }
        uint64_t latency=0;
        REQUIRE(gfg_x11_wait_visible_pair(x,window,extent.width,extent.height,
                expected,expected,1500000000ull,&latency));
        ++visible;
        ++output_visible;
        last_level=expected;
        seen[index]=1;
        fprintf(stderr,"GSF_LOADER_LIVE_APP frame=%u virtual_present=1 x11_visible=1 latency_us=%llu\\n",
            frame,(unsigned long long)(latency/1000));
    }
    REQUIRE(visible==8);
    REQUIRE(!interleave || intermediate_visible==7);
    REQUIRE(!interleave || output_visible==15);
    if(interleave)
        fprintf(stderr,"GSF_LOADER_SPLIT_APP output_visible=%u original=%u intermediate=%u x11_distinct_pixels=1 PASS\n",
            output_visible,visible,intermediate_visible);
    TRY(vkDeviceWaitIdle(device));
    vkDestroyFence(device,rendering,NULL);
    vkDestroySemaphore(device,image_ready,NULL);
    vkDestroySemaphore(device,render_done,NULL);
    vkDestroyCommandPool(device,pool,NULL);
    vkDestroySwapchainKHR(device,virtual_handle,NULL);
    fprintf(stderr,"GSF_LOADER_LIVE_APP 8 GPU-rendered real source frames visible through one output WSI PASS\\n");

    vkDestroyDevice(device,NULL);
    vkDestroySurfaceKHR(instance,surface,NULL);
    vkDestroyInstance(instance,NULL);
    xcb_destroy_window(x,window);xcb_disconnect(x);
    puts("GSF loader-installed virtual Acquire->Render->Present->X11 compositor PASS (not Deck)");
    return 0;
}
