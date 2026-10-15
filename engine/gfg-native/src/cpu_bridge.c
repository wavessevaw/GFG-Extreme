#define _POSIX_C_SOURCE 200809L
/* SPDX-License-Identifier: GPL-3.0-or-later
 *
 * GFG Native CPU transport for the TE8 LMC generator.
 * This deliberately favours correctness and isolation over performance.
 * Copy real presentable swapchain image -> mapped HOST_VISIBLE staging,
 * feed RGB to OWN Temporal Engine, read generated RGB, upload it to an
 * independently acquired swapchain image, present synthetic BEFORE real.
 * No MAKO, no proprietary shaders, no Lossless.dll, no external-FD import.
 *
 * The transport is opt-in, synchronous, SDR8-only, single-swapchain/queue.
 * Inability to initialize returns NULL and leaves normal WSI untouched.
 * Once we have consumed the application's binary render semaphores the
 * fallback is a forward present with waitSemaphoreCount=0 only AFTER the
 * source copy fence signals, so application frame delivery stays correct.
 */
#include "cpu_bridge.h"
#include "te_engine.h"
#include <limits.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#define LOAD(d, name) ((PFN_vk##name)(d)->gdpa((d)->device,"vk" #name))
#define FN(name) PFN_vk##name name
#define COLOR_BPP 4u

struct gfg_cpu_fg {
    VkDevice device;
    VkPhysicalDevice physical;
    VkQueue queue;
    VkSwapchainKHR swapchain;
    uint32_t family;
    VkExtent2D extent;
    VkFormat format;
    PFN_vkGetDeviceProcAddr gdpa;
    FN(CreateBuffer);
    FN(GetBufferMemoryRequirements);
    FN(AllocateMemory);
    FN(BindBufferMemory);
    FN(MapMemory);
    FN(UnmapMemory);
    FN(FreeMemory);
    FN(DestroyBuffer);
    FN(FlushMappedMemoryRanges);
    FN(InvalidateMappedMemoryRanges);
    FN(CreateCommandPool);
    FN(DestroyCommandPool);
    FN(AllocateCommandBuffers);
    FN(ResetCommandBuffer);
    FN(BeginCommandBuffer);
    FN(EndCommandBuffer);
    FN(CmdPipelineBarrier);
    FN(CmdCopyImageToBuffer);
    FN(CmdCopyBufferToImage);
    FN(CreateSemaphore);
    FN(DestroySemaphore);
    FN(CreateFence);
    FN(DestroyFence);
    FN(ResetFences);
    FN(WaitForFences);
    FN(QueueSubmit);
    FN(QueueWaitIdle);
    FN(AcquireNextImageKHR);
    FN(GetSwapchainImagesKHR);
    VkImage *images;
    uint32_t image_count;
    VkBuffer stage;
    VkDeviceMemory memory;
    void *mapped;
    VkDeviceSize allocation_bytes;
    VkDeviceSize atom_bytes;
    int coherent;
    VkCommandPool pool;
    VkCommandBuffer command;
    VkFence fence;
    VkSemaphore acquire_sem;
    VkSemaphore ready_sem;
    te_device *engine;
    te_context *context;
    uint8_t *rgb_real;
    uint8_t *rgb_generated;
    uint32_t source_slot;
    uint64_t real_frames;
    uint64_t synthetic_frames;
    uint64_t errors;
    uint64_t skipped;
    int permanently_disabled;
    bool log;
};

static void fail(const char *event, VkResult value) {
    fprintf(stderr,"[gfg-native] %s vkresult=%d\n",event,value);
}
static bool ok(VkResult r) { return r==VK_SUCCESS; }
static bool coherent_flush(gfg_cpu_fg *fg, VkBool32 invalidate) {
    if(fg->coherent) return true;
    VkMappedMemoryRange range={.sType=VK_STRUCTURE_TYPE_MAPPED_MEMORY_RANGE,
        .memory=fg->memory,.offset=0,.size=VK_WHOLE_SIZE};
    const VkResult result=invalidate
        ? fg->InvalidateMappedMemoryRanges(fg->device,1,&range)
        : fg->FlushMappedMemoryRanges(fg->device,1,&range);
    return ok(result);
}
static bool memory_type(VkPhysicalDeviceMemoryProperties *props,
        uint32_t mask, uint32_t *index, int *coherent) {
    for(int pass=0;pass<2;pass++)for(uint32_t i=0;i<props->memoryTypeCount;i++) {
        const VkMemoryPropertyFlags flags=props->memoryTypes[i].propertyFlags;
        if(!(mask&(1u<<i)) || !(flags&VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT)) continue;
        if(pass==0 && !(flags&VK_MEMORY_PROPERTY_HOST_COHERENT_BIT)) continue;
        *index=i;*coherent=!!(flags&VK_MEMORY_PROPERTY_HOST_COHERENT_BIT);return true;
    }
    return false;
}
static bool record_image_copy(gfg_cpu_fg *fg, VkImage image,
        uint32_t direction) {
    /* direction 0 = image -> staging; direction 1 = staging -> image */
    if(!ok(fg->ResetCommandBuffer(fg->command,0))) return false;
    VkCommandBufferBeginInfo begin={.sType=VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO,
        .flags=VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT};
    if(!ok(fg->BeginCommandBuffer(fg->command,&begin))) return false;
    VkImageMemoryBarrier before={.sType=VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER,
        .srcAccessMask=0,
        .dstAccessMask=direction?VK_ACCESS_TRANSFER_WRITE_BIT:VK_ACCESS_TRANSFER_READ_BIT,
        .oldLayout=direction?VK_IMAGE_LAYOUT_UNDEFINED:VK_IMAGE_LAYOUT_PRESENT_SRC_KHR,
        .newLayout=direction?VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL:VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL,
        .srcQueueFamilyIndex=VK_QUEUE_FAMILY_IGNORED,
        .dstQueueFamilyIndex=VK_QUEUE_FAMILY_IGNORED,
        .image=image,
        .subresourceRange={VK_IMAGE_ASPECT_COLOR_BIT,0,1,0,1}};
    fg->CmdPipelineBarrier(fg->command,VK_PIPELINE_STAGE_TRANSFER_BIT,
        VK_PIPELINE_STAGE_TRANSFER_BIT,0,0,NULL,0,NULL,1,&before);
    VkBufferImageCopy copy={.bufferOffset=0,.bufferRowLength=0,.bufferImageHeight=0,
        .imageSubresource={VK_IMAGE_ASPECT_COLOR_BIT,0,0,1},
        .imageExtent={fg->extent.width,fg->extent.height,1}};
    if(direction)
        fg->CmdCopyBufferToImage(fg->command,fg->stage,image,
            VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL,1,&copy);
    else
        fg->CmdCopyImageToBuffer(fg->command,image,
            VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL,fg->stage,1,&copy);
    VkImageMemoryBarrier after=before;
    after.srcAccessMask=direction?VK_ACCESS_TRANSFER_WRITE_BIT:VK_ACCESS_TRANSFER_READ_BIT;
    after.dstAccessMask=0;
    after.oldLayout=before.newLayout;
    after.newLayout=VK_IMAGE_LAYOUT_PRESENT_SRC_KHR;
    fg->CmdPipelineBarrier(fg->command,VK_PIPELINE_STAGE_TRANSFER_BIT,
        VK_PIPELINE_STAGE_BOTTOM_OF_PIPE_BIT,0,0,NULL,0,NULL,1,&after);
    return ok(fg->EndCommandBuffer(fg->command));
}
static bool submit_wait(gfg_cpu_fg *fg, uint32_t sem_count,
        const VkSemaphore *sems, VkSemaphore signal) {
    VkPipelineStageFlags *stages=NULL;
    if(sem_count) {
        stages=calloc(sem_count,sizeof(*stages));
        if(!stages) return false;
        for(uint32_t i=0;i<sem_count;i++)stages[i]=VK_PIPELINE_STAGE_TRANSFER_BIT;
    }
    VkSubmitInfo si={.sType=VK_STRUCTURE_TYPE_SUBMIT_INFO,
        .waitSemaphoreCount=sem_count,.pWaitSemaphores=sems,
        .pWaitDstStageMask=stages,
        .commandBufferCount=1,.pCommandBuffers=&fg->command,
        .signalSemaphoreCount=signal?1u:0u,.pSignalSemaphores=signal?&signal:NULL};
    VkResult result=fg->ResetFences(fg->device,1,&fg->fence);
    if(result==VK_SUCCESS)
        result=fg->QueueSubmit(fg->queue,1,&si,fg->fence);
    free(stages);
    if(!ok(result)){fail("queue-submit",result);return false;}
    /* Do NOT replay the game's consumed semaphore on a fallback path.
     * The captured copy must finish before readback or forwarding the real
     * present without those binary waits. */
    result=fg->WaitForFences(fg->device,1,&fg->fence,VK_TRUE,UINT64_MAX);
    if(!ok(result)){fail("queue-wait",result);return false;}
    return true;
}
static uint32_t sample_color(const uint8_t *p, VkFormat fmt, uint32_t c) {
    return p[fmt==VK_FORMAT_B8G8R8A8_UNORM ? 2u-c:c];
}
static void rgba_to_rgb(gfg_cpu_fg *fg) {
    const uint8_t *p=fg->mapped;
    const size_t pixels=(size_t)fg->extent.width*fg->extent.height;
    for(size_t k=0;k<pixels;k++)for(uint32_t c=0;c<3;c++)
        fg->rgb_real[k*3+c]=(uint8_t)sample_color(p+k*4,fg->format,c);
}
static void rgb_to_rgba(gfg_cpu_fg *fg) {
    uint8_t *p=fg->mapped;
    const size_t pixels=(size_t)fg->extent.width*fg->extent.height;
    for(size_t k=0;k<pixels;k++){
        for(uint32_t c=0;c<3;c++){
            const uint32_t target=fg->format==VK_FORMAT_B8G8R8A8_UNORM?2-c:c;
            p[k*4+target]=fg->rgb_generated[k*3+c];
        }
        p[k*4+3]=255;
    }
}
static bool run_te(gfg_cpu_fg *fg) {
    uint32_t slot=fg->source_slot;
    if(te_upload_rgb(fg->context,slot,fg->rgb_real)!=VK_SUCCESS) {
        fprintf(stderr,"[gfg-native] TE upload: %s\n",te_last_error());return false;
    }
    te_submit s={0};
    s.slot=slot;
    s.count=fg->real_frames?1:0;
    s.timestamps[0]=0.5f;
    s.download=1;
    const char *tier=getenv("GFG_NATIVE_LMC_TIER");
    if(tier && tier[0]>='0' && tier[0]<='2' && tier[1]=='\0')
        s.lmc_tier=tier[0]-'0';
    VkResult v=te_submit_frame(fg->context,&s);
    if(v!=VK_SUCCESS){fail("te-submit",v);return false;}
    /* This is a correctness-first CPU bridge: a bounded wait lets the game
     * still see a real frame when compute is too slow. */
    uint64_t budget=250000000ULL;
    const char *budget_env=getenv("GFG_NATIVE_BUDGET_MS");
    if(budget_env && *budget_env) {
        char *end=NULL;
        const unsigned long raw=strtoul(budget_env,&end,10);
        if(end && !*end && raw>=10 && raw<=5000)
            budget=(uint64_t)raw*1000000ULL;
    }
    struct timespec since={0}, until={0};
    clock_gettime(CLOCK_MONOTONIC,&since);
    const int ready=te_context_idle(fg->context,budget);
    clock_gettime(CLOCK_MONOTONIC,&until);
    if(fg->log) fprintf(stderr,
        "[gfg-native] TE pair slot=%u frame=%llu tier=%d ready=%d waited_ms=%.1f\n",
        slot,(unsigned long long)fg->real_frames,s.lmc_tier,ready,
        (until.tv_sec-since.tv_sec)*1000.0+(until.tv_nsec-since.tv_nsec)/1000000.0);
    if(!ready){
        ++fg->skipped;
        return false;
    }
    if(!fg->real_frames)return true;
    if(te_download_rgb(fg->context,0,fg->rgb_generated)!=VK_SUCCESS) {
        fprintf(stderr,"[gfg-native] TE download: %s\n",te_last_error());return false;
    }
    return true;
}
static bool present_generated(gfg_cpu_fg *fg, PFN_vkQueuePresentKHR next) {
    uint32_t idx=0;
    VkResult r=fg->AcquireNextImageKHR(fg->device,fg->swapchain,0,
        fg->acquire_sem,VK_NULL_HANDLE,&idx);
    if((r!=VK_SUCCESS && r!=VK_SUBOPTIMAL_KHR)||idx>=fg->image_count) {
        ++fg->skipped;
        return false;
    }
    rgb_to_rgba(fg);
    if(!coherent_flush(fg,VK_FALSE) ||
       !record_image_copy(fg,fg->images[idx],1) ||
       !submit_wait(fg,1,&fg->acquire_sem,fg->ready_sem)) {
        ++fg->errors;
        fg->permanently_disabled=1;
        return false;
    }
    VkPresentInfoKHR output={.sType=VK_STRUCTURE_TYPE_PRESENT_INFO_KHR,
        .waitSemaphoreCount=1,.pWaitSemaphores=&fg->ready_sem,
        .swapchainCount=1,.pSwapchains=&fg->swapchain,.pImageIndices=&idx};
    r=next(fg->queue,&output);
    if(r!=VK_SUCCESS && r!=VK_SUBOPTIMAL_KHR) {
        ++fg->errors;
        fg->permanently_disabled=1;
        return false;
    }
    /* Ensure the WSI consumed the ready semaphore before reusing it, and
     * preserve FIFO order ahead of the application's real frame. */
    r=fg->QueueWaitIdle(fg->queue);
    if(r!=VK_SUCCESS){fg->permanently_disabled=1;return false;}
    fg->synthetic_frames++;
    if(fg->log && fg->synthetic_frames%30==1)
        fprintf(stderr,"[gfg-native] generated=%llu real=%llu skipped=%llu errors=%llu\n",
            (unsigned long long)fg->synthetic_frames,
            (unsigned long long)fg->real_frames,
            (unsigned long long)fg->skipped,
            (unsigned long long)fg->errors);
    return true;
}

gfg_cpu_fg *gfg_cpu_fg_create(VkInstance instance,
        PFN_vkGetInstanceProcAddr gipa, VkPhysicalDevice physical,
        VkDevice device, PFN_vkGetDeviceProcAddr gdpa,
        VkSwapchainKHR swapchain, VkExtent2D extent, VkFormat format,
        VkQueue queue, uint32_t family) {
    if(!physical || !device || !queue || !instance || !gipa || !gdpa ||
       !extent.width || !extent.height || extent.width>3840 || extent.height>2160 ||
       (format!=VK_FORMAT_B8G8R8A8_UNORM && format!=VK_FORMAT_R8G8B8A8_UNORM))
        return NULL;
    gfg_cpu_fg *fg=calloc(1,sizeof(*fg));
    if(!fg)return NULL;
    fg->device=device;fg->physical=physical;fg->queue=queue;
    fg->gdpa=gdpa;fg->swapchain=swapchain;fg->extent=extent;fg->format=format;
    fg->family=family;fg->log=getenv("GFG_NATIVE_TRACE")!=NULL;
#define RESOLVE(name) fg->name=LOAD(fg,name); if(!fg->name) goto fail
    RESOLVE(CreateBuffer);
    RESOLVE(GetBufferMemoryRequirements);
    RESOLVE(AllocateMemory);
    RESOLVE(BindBufferMemory);
    RESOLVE(MapMemory);
    RESOLVE(UnmapMemory);
    RESOLVE(FreeMemory);
    RESOLVE(DestroyBuffer);
    RESOLVE(FlushMappedMemoryRanges);
    RESOLVE(InvalidateMappedMemoryRanges);
    RESOLVE(CreateCommandPool);
    RESOLVE(DestroyCommandPool);
    RESOLVE(AllocateCommandBuffers);
    RESOLVE(ResetCommandBuffer);
    RESOLVE(BeginCommandBuffer);
    RESOLVE(EndCommandBuffer);
    RESOLVE(CmdPipelineBarrier);
    RESOLVE(CmdCopyImageToBuffer);
    RESOLVE(CmdCopyBufferToImage);
    RESOLVE(CreateSemaphore);
    RESOLVE(DestroySemaphore);
    RESOLVE(CreateFence);
    RESOLVE(DestroyFence);
    RESOLVE(ResetFences);
    RESOLVE(WaitForFences);
    RESOLVE(QueueSubmit);
    RESOLVE(QueueWaitIdle);
    RESOLVE(AcquireNextImageKHR);
    RESOLVE(GetSwapchainImagesKHR);
#undef RESOLVE
    PFN_vkGetPhysicalDeviceMemoryProperties mp=(PFN_vkGetPhysicalDeviceMemoryProperties)
        gipa(instance,"vkGetPhysicalDeviceMemoryProperties");
    PFN_vkGetPhysicalDeviceProperties2 props2=(PFN_vkGetPhysicalDeviceProperties2)
        gipa(instance,"vkGetPhysicalDeviceProperties2");
    if(!mp || !props2)goto fail;
    uint32_t n=0;
    if(fg->GetSwapchainImagesKHR(device,swapchain,&n,NULL)!=VK_SUCCESS||
       n<2||n>32)goto fail;
    fg->images=calloc(n,sizeof(*fg->images));
    if(!fg->images||fg->GetSwapchainImagesKHR(device,swapchain,&n,fg->images)!=VK_SUCCESS)
        goto fail;
    fg->image_count=n;
    const size_t pixels=(size_t)extent.width*extent.height;
    if(pixels>SIZE_MAX/4u)goto fail;
    const VkDeviceSize bytes=(VkDeviceSize)pixels*COLOR_BPP;
    fg->rgb_real=malloc(pixels*3u);
    fg->rgb_generated=malloc(pixels*3u);
    if(!fg->rgb_real||!fg->rgb_generated)goto fail;
    VkBufferCreateInfo bi={.sType=VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO,
        .size=bytes,.usage=VK_BUFFER_USAGE_TRANSFER_SRC_BIT|VK_BUFFER_USAGE_TRANSFER_DST_BIT,
        .sharingMode=VK_SHARING_MODE_EXCLUSIVE};
    if(!ok(fg->CreateBuffer(device,&bi,NULL,&fg->stage)))goto fail;
    VkMemoryRequirements mr;
    fg->GetBufferMemoryRequirements(device,fg->stage,&mr);
    VkPhysicalDeviceMemoryProperties types;
    mp(physical,&types);
    uint32_t index=0;
    if(!memory_type(&types,mr.memoryTypeBits,&index,&fg->coherent))goto fail;
    VkMemoryAllocateInfo ai={.sType=VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO,
        .allocationSize=mr.size,.memoryTypeIndex=index};
    if(!ok(fg->AllocateMemory(device,&ai,NULL,&fg->memory)))goto fail;
    fg->allocation_bytes=mr.size;
    if(!ok(fg->BindBufferMemory(device,fg->stage,fg->memory,0)))goto fail;
    if(!ok(fg->MapMemory(device,fg->memory,0,VK_WHOLE_SIZE,0,&fg->mapped)))goto fail;
    VkCommandPoolCreateInfo pool={.sType=VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO,
        .flags=VK_COMMAND_POOL_CREATE_RESET_COMMAND_BUFFER_BIT,.queueFamilyIndex=family};
    if(!ok(fg->CreateCommandPool(device,&pool,NULL,&fg->pool)))goto fail;
    VkCommandBufferAllocateInfo cmd={.sType=VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO,
        .commandPool=fg->pool,.level=VK_COMMAND_BUFFER_LEVEL_PRIMARY,
        .commandBufferCount=1};
    if(!ok(fg->AllocateCommandBuffers(device,&cmd,&fg->command)))goto fail;
    VkFenceCreateInfo fci={.sType=VK_STRUCTURE_TYPE_FENCE_CREATE_INFO};
    if(!ok(fg->CreateFence(device,&fci,NULL,&fg->fence)))goto fail;
    VkSemaphoreCreateInfo sci={.sType=VK_STRUCTURE_TYPE_SEMAPHORE_CREATE_INFO};
    if(!ok(fg->CreateSemaphore(device,&sci,NULL,&fg->acquire_sem))||
       !ok(fg->CreateSemaphore(device,&sci,NULL,&fg->ready_sem)))goto fail;

    VkPhysicalDeviceIDProperties id={.sType=VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_ID_PROPERTIES};
    VkPhysicalDeviceProperties2 properties={.sType=VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_PROPERTIES_2,
        .pNext=&id};
    props2(physical,&properties);
    te_device_desc dd={.match_uuid=1};
    memcpy(dd.device_uuid,id.deviceUUID,VK_UUID_SIZE);
    if(te_device_create(&dd,&fg->engine)!=VK_SUCCESS){
        fprintf(stderr,"[gfg-native] TE device: %s\n",te_last_error());goto fail;
    }
    te_context_desc cd;
    te_context_desc_default(&cd,extent.width,extent.height,1);
    cd.params.algorithm=TE_ALGO_LMC;
    cd.host_io=1;
    if(te_context_create(fg->engine,&cd,&fg->context)!=VK_SUCCESS){
        fprintf(stderr,"[gfg-native] TE context: %s\n",te_last_error());goto fail;
    }
    if(fg->log)fprintf(stderr,"[gfg-native] OWN LMC CPU bridge active: %ux%u format=%d\n",
        extent.width,extent.height,format);
    return fg;
fail:
    gfg_cpu_fg_destroy(fg);
    return NULL;
}
VkResult gfg_cpu_fg_present(gfg_cpu_fg *fg, const VkPresentInfoKHR *original,
                            PFN_vkQueuePresentKHR next) {
    if(!fg || !original || !next)return VK_ERROR_INITIALIZATION_FAILED;
    if(fg->permanently_disabled)return next(fg->queue,original);
    const uint32_t index=original->pImageIndices[0];
    if(index>=fg->image_count)return next(fg->queue,original);
    if(!record_image_copy(fg,fg->images[index],0))
        return next(fg->queue,original); /* app semaphore untouched */
    if(!submit_wait(fg,original->waitSemaphoreCount,
            original->pWaitSemaphores,VK_NULL_HANDLE)) {
        /* A failing submit MAY have consumed waits. Never replay an unknown
         * binary semaphore. Device-loss failure propagates, not a fake success. */
        fg->permanently_disabled=1;
        return VK_ERROR_DEVICE_LOST;
    }
    VkPresentInfoKHR real=*original;
    real.waitSemaphoreCount=0;
    real.pWaitSemaphores=NULL;
    if(!coherent_flush(fg,VK_TRUE)) { fg->permanently_disabled=1; }
    if(!fg->permanently_disabled) {
        rgba_to_rgb(fg);
        const bool completed=run_te(fg);
        if(completed && fg->real_frames) (void)present_generated(fg,next);
        if(!completed && fg->context && !te_context_idle(fg->context,0)) {
            /* Avoid overwriting source slot while old compute work persists.
             * New pairs resume only after a context reset in a later version.
             * Real frames remain unaffected after this disable. */
            fg->permanently_disabled=1;
        }
        fg->source_slot ^= 1u;
    }
    fg->real_frames++;
    return next(fg->queue,&real);
}
void gfg_cpu_fg_destroy(gfg_cpu_fg *fg) {
    if(!fg)return;
    if(fg->log)fprintf(stderr,
        "[gfg-native] CPU bridge retired real=%llu generated=%llu missed=%llu errors=%llu\n",
        (unsigned long long)fg->real_frames,
        (unsigned long long)fg->synthetic_frames,
        (unsigned long long)fg->skipped,
        (unsigned long long)fg->errors);
    if(fg->context)te_context_destroy(fg->context);
    if(fg->engine)te_device_destroy(fg->engine);
    if(fg->device && fg->QueueWaitIdle)(void)fg->QueueWaitIdle(fg->queue);
    if(fg->device && fg->DestroySemaphore) {
        if(fg->ready_sem)fg->DestroySemaphore(fg->device,fg->ready_sem,NULL);
        if(fg->acquire_sem)fg->DestroySemaphore(fg->device,fg->acquire_sem,NULL);
    }
    if(fg->device && fg->DestroyFence && fg->fence)
        fg->DestroyFence(fg->device,fg->fence,NULL);
    if(fg->device && fg->DestroyCommandPool && fg->pool)
        fg->DestroyCommandPool(fg->device,fg->pool,NULL);
    if(fg->device && fg->UnmapMemory && fg->mapped)
        fg->UnmapMemory(fg->device,fg->memory);
    if(fg->device && fg->DestroyBuffer && fg->stage)
        fg->DestroyBuffer(fg->device,fg->stage,NULL);
    if(fg->device && fg->FreeMemory && fg->memory)
        fg->FreeMemory(fg->device,fg->memory,NULL);
    free(fg->images);
    free(fg->rgb_real);
    free(fg->rgb_generated);
    free(fg);
}
uint64_t gfg_cpu_fg_generated(const gfg_cpu_fg *fg) {
    return fg?fg->synthetic_frames:0;
}
