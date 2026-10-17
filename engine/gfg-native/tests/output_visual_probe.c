#define _POSIX_C_SOURCE 200809L
/* SPDX-License-Identifier: GPL-3.0-or-later
 * GSF Frame Output Engine standalone pixel/WSI probe.
 * Red A -> green simulated midpoint -> blue B, driven through one owned
 * Vulkan swapchain. The green frame is intentionally a diagnostic COLOR,
 * NOT AI/generated interpolation, NOT a captured game image.
 * Headless CI checks Vulkan present acceptance, not OLED scanout.
 */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <vulkan/vulkan.h>
#include <vulkan/vulkan_xcb.h>
#include <xcb/xcb.h>
#include <time.h>

#ifdef GFG_NATIVE_TEST_SMALL
#define TEST_WIDTH 96u
#define TEST_HEIGHT 64u
#else
#define TEST_WIDTH 640u
#define TEST_HEIGHT 360u
#endif

#define TRY(x) do { VkResult r_ = (x); if (r_ != VK_SUCCESS && r_ != VK_SUBOPTIMAL_KHR) { \
  fprintf(stderr, "Vulkan failure %s => %d at %d\n", #x, r_, __LINE__); return 1; \
} } while (0)
#define REQUIRE(x) do { if (!(x)) { fprintf(stderr, "Requirement failed: %s line %d\n", #x, __LINE__); return 1; } } while (0)

static int supports(VkPhysicalDevice physical, const char *ext) {
    uint32_t count=0;
    if (vkEnumerateDeviceExtensionProperties(physical,NULL,&count,NULL)!=VK_SUCCESS) return 0;
    VkExtensionProperties *p=calloc(count,sizeof(*p));
    if (!p) return 0;
    int yes=0;
    if (vkEnumerateDeviceExtensionProperties(physical,NULL,&count,p)==VK_SUCCESS)
        for (uint32_t k=0;k<count;k++) if (!strcmp(ext,p[k].extensionName)) {yes=1;break;}
    free(p);
    return yes;
}
static uint32_t between(uint32_t x,uint32_t low,uint32_t high) {
    if(x<low) return low;
    return x>high?high:x;
}

int main(void) {
    int screen_no=0;
    xcb_connection_t *xc=xcb_connect(NULL,&screen_no);
    REQUIRE(xc && !xcb_connection_has_error(xc));
    const xcb_setup_t *setup=xcb_get_setup(xc);
    xcb_screen_iterator_t it=xcb_setup_roots_iterator(setup);
    for(int k=0;k<screen_no;k++) xcb_screen_next(&it);
    REQUIRE(it.data);
    xcb_screen_t *screen=it.data;
    xcb_window_t window=xcb_generate_id(xc);
    const uint32_t opts[]={screen->black_pixel,XCB_EVENT_MASK_EXPOSURE};
    xcb_create_window(xc,XCB_COPY_FROM_PARENT,window,screen->root,0,0,TEST_WIDTH,TEST_HEIGHT,0,
        XCB_WINDOW_CLASS_INPUT_OUTPUT,screen->root_visual,
        XCB_CW_BACK_PIXEL|XCB_CW_EVENT_MASK,opts);
    xcb_map_window(xc,window);
    REQUIRE(xcb_flush(xc)>0);

    const char *instance_extensions[]={"VK_KHR_surface","VK_KHR_xcb_surface"};
    VkApplicationInfo app={.sType=VK_STRUCTURE_TYPE_APPLICATION_INFO,
        .pApplicationName="gfg-frame-output-probe",
        .pEngineName="gfg-temporal",
        .apiVersion=VK_API_VERSION_1_2};
    VkInstanceCreateInfo ci={.sType=VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO,
        .pApplicationInfo=&app,.enabledExtensionCount=2,
        .ppEnabledExtensionNames=instance_extensions};
    VkInstance instance=VK_NULL_HANDLE;
    TRY(vkCreateInstance(&ci,NULL,&instance));
    VkXcbSurfaceCreateInfoKHR sci={.sType=VK_STRUCTURE_TYPE_XCB_SURFACE_CREATE_INFO_KHR,
        .connection=xc,.window=window};
    VkSurfaceKHR surface=VK_NULL_HANDLE;
    TRY(vkCreateXcbSurfaceKHR(instance,&sci,NULL,&surface));

    uint32_t count=0;
    TRY(vkEnumeratePhysicalDevices(instance,&count,NULL));
    REQUIRE(count>0);
    VkPhysicalDevice *phys=calloc(count,sizeof(*phys));
    REQUIRE(phys);
    TRY(vkEnumeratePhysicalDevices(instance,&count,phys));
    VkPhysicalDevice physical=VK_NULL_HANDLE;
    uint32_t family=UINT32_MAX;
    for(uint32_t i=0;i<count && !physical;i++) {
        if(!supports(phys[i],"VK_KHR_swapchain")) continue;
        uint32_t qcount=0;
        vkGetPhysicalDeviceQueueFamilyProperties(phys[i],&qcount,NULL);
        VkQueueFamilyProperties *families=calloc(qcount,sizeof(*families));
        REQUIRE(families);
        vkGetPhysicalDeviceQueueFamilyProperties(phys[i],&qcount,families);
        for(uint32_t q=0;q<qcount;q++){
            VkBool32 presented=VK_FALSE;
            if(families[q].queueFlags & VK_QUEUE_GRAPHICS_BIT)
                TRY(vkGetPhysicalDeviceSurfaceSupportKHR(phys[i],q,surface,&presented));
            if(presented){physical=phys[i];family=q;break;}
        }
        free(families);
    }
    free(phys);
    REQUIRE(physical && family!=UINT32_MAX);
    const float priority=1.0f;
    VkDeviceQueueCreateInfo qi={.sType=VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO,
        .queueFamilyIndex=family,.queueCount=1,.pQueuePriorities=&priority};
    const char *device_ext[]={"VK_KHR_swapchain"};
    VkDeviceCreateInfo di={.sType=VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO,
        .queueCreateInfoCount=1,.pQueueCreateInfos=&qi,
        .enabledExtensionCount=1,.ppEnabledExtensionNames=device_ext};
    VkDevice device=VK_NULL_HANDLE;
    TRY(vkCreateDevice(physical,&di,NULL,&device));
    VkQueue queue=VK_NULL_HANDLE;
    vkGetDeviceQueue(device,family,0,&queue);
    REQUIRE(queue);

    VkSurfaceCapabilitiesKHR caps;
    TRY(vkGetPhysicalDeviceSurfaceCapabilitiesKHR(physical,surface,&caps));
    REQUIRE(caps.supportedUsageFlags&VK_IMAGE_USAGE_TRANSFER_DST_BIT);
    const int verify_pixels=getenv("GFG_FOE_VISUAL_VERIFY") &&
        !strcmp(getenv("GFG_FOE_VISUAL_VERIFY"),"1");
    if(verify_pixels) REQUIRE(caps.supportedUsageFlags&VK_IMAGE_USAGE_TRANSFER_SRC_BIT);
    VkExtent2D ext=caps.currentExtent;
    if(ext.width==UINT32_MAX) {
        ext.width=between(TEST_WIDTH,caps.minImageExtent.width,caps.maxImageExtent.width);
        ext.height=between(TEST_HEIGHT,caps.minImageExtent.height,caps.maxImageExtent.height);
    }
    uint32_t nformats=0;
    TRY(vkGetPhysicalDeviceSurfaceFormatsKHR(physical,surface,&nformats,NULL));
    REQUIRE(nformats>0);
    VkSurfaceFormatKHR *formats=calloc(nformats,sizeof(*formats)); REQUIRE(formats);
    TRY(vkGetPhysicalDeviceSurfaceFormatsKHR(physical,surface,&nformats,formats));
    VkSurfaceFormatKHR color=formats[0];
    const char *want_srgb=getenv("GFG_NATIVE_TEST_SRGB");
    const int srgb=want_srgb && !strcmp(want_srgb,"1");
    const VkFormat wanted=srgb?VK_FORMAT_B8G8R8A8_SRGB:VK_FORMAT_B8G8R8A8_UNORM;
    int found=0;
    for(uint32_t i=0;i<nformats;i++)if(formats[i].format==wanted)
        {color=formats[i];found=1;break;}
    free(formats);
    if(srgb || verify_pixels) REQUIRE(found);
    if(srgb)fprintf(stderr,"GFG native: WSI SRGB format=%d selected\n",(int)color.format);
    uint32_t minimum=caps.minImageCount<2?2:caps.minImageCount;
    if(caps.maxImageCount && minimum>caps.maxImageCount) minimum=caps.maxImageCount;
    VkSwapchainCreateInfoKHR swci={.sType=VK_STRUCTURE_TYPE_SWAPCHAIN_CREATE_INFO_KHR,
        .surface=surface,.minImageCount=minimum,.imageFormat=color.format,
        .imageColorSpace=color.colorSpace,.imageExtent=ext,.imageArrayLayers=1,
        .imageUsage=VK_IMAGE_USAGE_TRANSFER_DST_BIT |
            (verify_pixels?VK_IMAGE_USAGE_TRANSFER_SRC_BIT:0u),
        .imageSharingMode=VK_SHARING_MODE_EXCLUSIVE,
        .preTransform=caps.currentTransform,.compositeAlpha=VK_COMPOSITE_ALPHA_OPAQUE_BIT_KHR,
        .presentMode=VK_PRESENT_MODE_FIFO_KHR,.clipped=VK_TRUE};
    if (!(caps.supportedCompositeAlpha&VK_COMPOSITE_ALPHA_OPAQUE_BIT_KHR)) {
        for(uint32_t bit=1;bit<=8;bit*=2) if(caps.supportedCompositeAlpha&bit)
            {swci.compositeAlpha=(VkCompositeAlphaFlagBitsKHR)bit;break;}
    }
    VkSwapchainKHR swapchain=VK_NULL_HANDLE;
    TRY(vkCreateSwapchainKHR(device,&swci,NULL,&swapchain));

    uint32_t image_count=0;
    TRY(vkGetSwapchainImagesKHR(device,swapchain,&image_count,NULL));
    REQUIRE(image_count>=minimum);
    VkImage *images=calloc(image_count,sizeof(*images));REQUIRE(images);
    TRY(vkGetSwapchainImagesKHR(device,swapchain,&image_count,images));
    VkCommandPoolCreateInfo poolci={.sType=VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO,
        .queueFamilyIndex=family,.flags=VK_COMMAND_POOL_CREATE_RESET_COMMAND_BUFFER_BIT};
    VkCommandPool pool=VK_NULL_HANDLE;
    TRY(vkCreateCommandPool(device,&poolci,NULL,&pool));
    VkCommandBufferAllocateInfo cbai={.sType=VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO,
        .commandPool=pool,.level=VK_COMMAND_BUFFER_LEVEL_PRIMARY,.commandBufferCount=1};
    VkCommandBuffer cmd=VK_NULL_HANDLE; TRY(vkAllocateCommandBuffers(device,&cbai,&cmd));
    VkSemaphoreCreateInfo semci={.sType=VK_STRUCTURE_TYPE_SEMAPHORE_CREATE_INFO};
    VkSemaphore acquired=VK_NULL_HANDLE, ready=VK_NULL_HANDLE;
    TRY(vkCreateSemaphore(device,&semci,NULL,&acquired));
    TRY(vkCreateSemaphore(device,&semci,NULL,&ready));
    unsigned char *seen=calloc(image_count,1);REQUIRE(seen);
    /* Read back one pixel of the ACTUAL GPU-cleared WSI image before present.
     * This proves pixel payloads reach the Vulkan output images, unlike an
     * FPS/queue counter; it still cannot prove physical scanout. */
    VkBuffer probe_buffer=VK_NULL_HANDLE;
    VkDeviceMemory probe_memory=VK_NULL_HANDLE;
    unsigned char *probe_pixel=NULL;
    if(verify_pixels){
        VkBufferCreateInfo bci={.sType=VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO,
            .size=4,.usage=VK_BUFFER_USAGE_TRANSFER_DST_BIT,
            .sharingMode=VK_SHARING_MODE_EXCLUSIVE};
        TRY(vkCreateBuffer(device,&bci,NULL,&probe_buffer));
        VkMemoryRequirements req;
        vkGetBufferMemoryRequirements(device,probe_buffer,&req);
        VkPhysicalDeviceMemoryProperties mem;
        vkGetPhysicalDeviceMemoryProperties(physical,&mem);
        uint32_t memory_type=UINT32_MAX;
        for(uint32_t i=0;i<mem.memoryTypeCount;i++)
            if((req.memoryTypeBits&(1u<<i)) &&
              (mem.memoryTypes[i].propertyFlags &
                (VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT|VK_MEMORY_PROPERTY_HOST_COHERENT_BIT)) ==
                (VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT|VK_MEMORY_PROPERTY_HOST_COHERENT_BIT)){
                memory_type=i;break;
            }
        REQUIRE(memory_type!=UINT32_MAX);
        VkMemoryAllocateInfo mai={.sType=VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO,
            .allocationSize=req.size,.memoryTypeIndex=memory_type};
        TRY(vkAllocateMemory(device,&mai,NULL,&probe_memory));
        TRY(vkBindBufferMemory(device,probe_buffer,probe_memory,0));
        void *mapped=NULL;
        TRY(vkMapMemory(device,probe_memory,0,4,0,&mapped));
        probe_pixel=mapped;
    }

    /* This is the actual output ownership boundary of the stage-1 probe:
     * three GPU images belong to our producer, NONE belong to the game's
     * swapchain. The single WSI swapchain receives a copy of their contents.
     * Real and TEST-synthetic images are identically represented. */
    VkImage producer[3]={VK_NULL_HANDLE,VK_NULL_HANDLE,VK_NULL_HANDLE};
    VkDeviceMemory producer_memory[3]={VK_NULL_HANDLE,VK_NULL_HANDLE,VK_NULL_HANDLE};
    unsigned producer_ready[3]={0,0,0};
    VkPhysicalDeviceMemoryProperties device_memory;
    vkGetPhysicalDeviceMemoryProperties(physical,&device_memory);
    for(unsigned k=0;k<3;k++){
        VkImageCreateInfo ici={.sType=VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO,
            .imageType=VK_IMAGE_TYPE_2D,.format=color.format,
            .extent={ext.width,ext.height,1},.mipLevels=1,.arrayLayers=1,
            .samples=VK_SAMPLE_COUNT_1_BIT,.tiling=VK_IMAGE_TILING_OPTIMAL,
            .usage=VK_IMAGE_USAGE_TRANSFER_SRC_BIT|VK_IMAGE_USAGE_TRANSFER_DST_BIT,
            .sharingMode=VK_SHARING_MODE_EXCLUSIVE,.initialLayout=VK_IMAGE_LAYOUT_UNDEFINED};
        TRY(vkCreateImage(device,&ici,NULL,&producer[k]));
        VkMemoryRequirements req;vkGetImageMemoryRequirements(device,producer[k],&req);
        uint32_t type=UINT32_MAX;
        for(uint32_t j=0;j<device_memory.memoryTypeCount;j++)
            if((req.memoryTypeBits&(1u<<j)) &&
                (device_memory.memoryTypes[j].propertyFlags&VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT)){
                type=j;break;
            }
        REQUIRE(type!=UINT32_MAX);
        VkMemoryAllocateInfo ma={.sType=VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO,
            .allocationSize=req.size,.memoryTypeIndex=type};
        TRY(vkAllocateMemory(device,&ma,NULL,&producer_memory[k]));
        TRY(vkBindImageMemory(device,producer[k],producer_memory[k],0));
    }

    PFN_vkQueuePresentKHR present_gipa=(PFN_vkQueuePresentKHR)
        vkGetInstanceProcAddr(instance,"vkQueuePresentKHR");
    PFN_vkQueuePresentKHR present_gdpa=(PFN_vkQueuePresentKHR)
        vkGetDeviceProcAddr(device,"vkQueuePresentKHR");
    REQUIRE(present_gipa && present_gdpa);
    uint32_t total=90u,delay_ms=150u;
    const char *frames=getenv("GFG_FOE_VISUAL_FRAMES");
    const char *interval=getenv("GFG_FOE_VISUAL_INTERVAL_MS");
    if(frames && *frames){ char *end;unsigned long n=strtoul(frames,&end,10);
        if(!*end && n>=3 && n<=2000)total=(uint32_t)n; }
    if(interval && *interval){ char *end;unsigned long n=strtoul(interval,&end,10);
        if(!*end && n<=500)delay_ms=(uint32_t)n; }
    fprintf(stderr,"[foe-probe] single_output_owner=1 real_pixels=red/blue midpoint_pixels=GREEN_DIAGNOSTIC only_WSI_not_scanout frames=%u delay_ms=%u\\n",total,delay_ms);
    for(uint32_t frame=0;frame<total;frame++) {
        uint32_t index=UINT32_MAX;
        TRY(vkAcquireNextImageKHR(device,swapchain,UINT64_MAX,acquired,VK_NULL_HANDLE,&index));
        REQUIRE(index<image_count);
        TRY(vkResetCommandBuffer(cmd,0));
        VkCommandBufferBeginInfo begin={.sType=VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO};
        TRY(vkBeginCommandBuffer(cmd,&begin));
        VkImageMemoryBarrier pre={.sType=VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER,
            .srcAccessMask=0,.dstAccessMask=VK_ACCESS_TRANSFER_WRITE_BIT,
            .oldLayout=seen[index]?VK_IMAGE_LAYOUT_PRESENT_SRC_KHR:VK_IMAGE_LAYOUT_UNDEFINED,
            .newLayout=VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL,
            .srcQueueFamilyIndex=VK_QUEUE_FAMILY_IGNORED,.dstQueueFamilyIndex=VK_QUEUE_FAMILY_IGNORED,
            .image=images[index],
            .subresourceRange={VK_IMAGE_ASPECT_COLOR_BIT,0,1,0,1}};
        vkCmdPipelineBarrier(cmd,VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT,
            VK_PIPELINE_STAGE_TRANSFER_BIT,0,0,NULL,0,NULL,1,&pre);
        /* Keep one output owner and send A, midpoint, B to the SAME WSI
         * surface. Green must never be reported as generated ML content. */
        const unsigned role=frame%3u; /* 0=A(red),1=mid(green),2=B(blue) */
        VkClearColorValue clear={.float32={
            role==0u?0.95f:0.08f,role==1u?0.95f:0.08f,
            role==2u?0.95f:0.08f,1.0f}};
        VkImageSubresourceRange range={VK_IMAGE_ASPECT_COLOR_BIT,0,1,0,1};
        if(!producer_ready[role]){
            VkImageMemoryBarrier init={.sType=VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER,
                .srcAccessMask=0,.dstAccessMask=VK_ACCESS_TRANSFER_WRITE_BIT,
                .oldLayout=VK_IMAGE_LAYOUT_UNDEFINED,
                .newLayout=VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL,
                .srcQueueFamilyIndex=VK_QUEUE_FAMILY_IGNORED,
                .dstQueueFamilyIndex=VK_QUEUE_FAMILY_IGNORED,
                .image=producer[role],.subresourceRange={VK_IMAGE_ASPECT_COLOR_BIT,0,1,0,1}};
            vkCmdPipelineBarrier(cmd,VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT,
                VK_PIPELINE_STAGE_TRANSFER_BIT,0,0,NULL,0,NULL,1,&init);
            vkCmdClearColorImage(cmd,producer[role],
                                 VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL,&clear,1,&range);
            init.srcAccessMask=VK_ACCESS_TRANSFER_WRITE_BIT;
            init.dstAccessMask=VK_ACCESS_TRANSFER_READ_BIT;
            init.oldLayout=VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL;
            init.newLayout=VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL;
            vkCmdPipelineBarrier(cmd,VK_PIPELINE_STAGE_TRANSFER_BIT,
                VK_PIPELINE_STAGE_TRANSFER_BIT,0,0,NULL,0,NULL,1,&init);
            producer_ready[role]=1;
        }
        /* One GPU copy into the sole output swapchain, independent of the
         * source image's lifetime and independent of source acquisition. */
        VkImageCopy full={.srcSubresource={VK_IMAGE_ASPECT_COLOR_BIT,0,0,1},
            .dstSubresource={VK_IMAGE_ASPECT_COLOR_BIT,0,0,1},
            .extent={ext.width,ext.height,1}};
        vkCmdCopyImage(cmd,producer[role],VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL,
            images[index],VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL,1,&full);
        if(verify_pixels) {
            VkImageMemoryBarrier tosrc=pre;
            tosrc.srcAccessMask=VK_ACCESS_TRANSFER_WRITE_BIT;
            tosrc.dstAccessMask=VK_ACCESS_TRANSFER_READ_BIT;
            tosrc.oldLayout=VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL;
            tosrc.newLayout=VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL;
            vkCmdPipelineBarrier(cmd,VK_PIPELINE_STAGE_TRANSFER_BIT,
                VK_PIPELINE_STAGE_TRANSFER_BIT,0,0,NULL,0,NULL,1,&tosrc);
            VkBufferImageCopy region={.bufferOffset=0,.bufferRowLength=0,
                .bufferImageHeight=0,.imageSubresource={VK_IMAGE_ASPECT_COLOR_BIT,0,0,1},
                .imageOffset={0,0,0},.imageExtent={1,1,1}};
            vkCmdCopyImageToBuffer(cmd,images[index],VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL,
                                   probe_buffer,1,&region);
            VkBufferMemoryBarrier host={.sType=VK_STRUCTURE_TYPE_BUFFER_MEMORY_BARRIER,
                .srcAccessMask=VK_ACCESS_TRANSFER_WRITE_BIT,
                .dstAccessMask=VK_ACCESS_HOST_READ_BIT,
                .srcQueueFamilyIndex=VK_QUEUE_FAMILY_IGNORED,
                .dstQueueFamilyIndex=VK_QUEUE_FAMILY_IGNORED,
                .buffer=probe_buffer,.offset=0,.size=4};
            vkCmdPipelineBarrier(cmd,VK_PIPELINE_STAGE_TRANSFER_BIT,
                VK_PIPELINE_STAGE_HOST_BIT,0,0,NULL,1,&host,0,NULL);
        }
        VkImageMemoryBarrier post=pre;
        post.srcAccessMask=verify_pixels?VK_ACCESS_TRANSFER_READ_BIT:VK_ACCESS_TRANSFER_WRITE_BIT;
        post.dstAccessMask=0;
        post.oldLayout=verify_pixels?VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL:VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL;
        post.newLayout=VK_IMAGE_LAYOUT_PRESENT_SRC_KHR;
        vkCmdPipelineBarrier(cmd,VK_PIPELINE_STAGE_TRANSFER_BIT,
            VK_PIPELINE_STAGE_BOTTOM_OF_PIPE_BIT,0,0,NULL,0,NULL,1,&post);
        TRY(vkEndCommandBuffer(cmd));
        VkPipelineStageFlags stage=VK_PIPELINE_STAGE_TRANSFER_BIT;
        VkSubmitInfo si={.sType=VK_STRUCTURE_TYPE_SUBMIT_INFO,
            .waitSemaphoreCount=1,.pWaitSemaphores=&acquired,.pWaitDstStageMask=&stage,
            .commandBufferCount=1,.pCommandBuffers=&cmd,
            .signalSemaphoreCount=1,.pSignalSemaphores=&ready};
        TRY(vkQueueSubmit(queue,1,&si,VK_NULL_HANDLE));
        VkPresentInfoKHR pi={.sType=VK_STRUCTURE_TYPE_PRESENT_INFO_KHR,
            .waitSemaphoreCount=1,.pWaitSemaphores=&ready,
            .swapchainCount=1,.pSwapchains=&swapchain,.pImageIndices=&index};
        if(frame%2==0) TRY(present_gipa(queue,&pi));
        else TRY(present_gdpa(queue,&pi));
        TRY(vkQueueWaitIdle(queue));
        if(verify_pixels){
            /* Expected BGRA byte ordering; assert dominant channel of
             * the colored TEST pixels, not success from WSI alone. */
            const unsigned dominant=role==0?2u:role==1?1u:0u;
            REQUIRE(probe_pixel[dominant]>=220u);
            REQUIRE(probe_pixel[(dominant+1u)%3u]<=65u);
            REQUIRE(probe_pixel[(dominant+2u)%3u]<=65u);
        }
        seen[index]=1;
        if(frame<9 || (frame%90u)==0u)
            fprintf(stderr,"[foe-probe] WSI_accept frame=%u role=%s color=%s\\n",
                    frame,role==0?"REAL_A":role==1?"TEST_MIDPOINT":"REAL_B",
                    role==0?"red":role==1?"green":"blue");
        if(delay_ms){ struct timespec pause={(time_t)(delay_ms/1000u),
                      (long)((delay_ms%1000u)*1000000u)};nanosleep(&pause,NULL); }
    }
    free(seen);
    for(unsigned i=0;i<3;++i){
        vkDestroyImage(device,producer[i],NULL);
        vkFreeMemory(device,producer_memory[i],NULL);
    }
    if(verify_pixels){
        vkUnmapMemory(device,probe_memory);
        vkDestroyBuffer(device,probe_buffer,NULL);
        vkFreeMemory(device,probe_memory,NULL);
        puts("[foe-probe] GPU PIXEL READBACK: ALL REAL/MID/REAL TEST PATTERNS VERIFIED");
    }
    vkDestroySemaphore(device,ready,NULL);
    vkDestroySemaphore(device,acquired,NULL);
    vkDestroyCommandPool(device,pool,NULL);
    free(images);
    vkDestroySwapchainKHR(device,swapchain,NULL);
    vkDestroyDevice(device,NULL);
    vkDestroySurfaceKHR(instance,surface,NULL);
    vkDestroyInstance(instance,NULL);
    xcb_destroy_window(xc,window);xcb_disconnect(xc);
    puts("GSF FOE probe: THREE owned offscreen GPU images -> ONE WSI swapchain; real A(red)->TEST mid(green)->real B(blue), no game capture or OLED scanout claim");
    return 0;
}
