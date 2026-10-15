/* SPDX-License-Identifier: GPL-3.0-or-later
 * Native same-device GPU transport. No pixel staging, host colour conversion,
 * private VkDevice, external FD or CPU motion fitting. Queue operations are
 * externally synchronized by the application's QueuePresent caller. Every
 * captured interval requests exactly t=1/3 and t=2/3; history/failure bypasses
 * are explicit and are never counted as synthetic presentation.
 */
#include "gpu_bridge.h"
#include "te_engine.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define RING 3
#define MAX_WAITS 64
#define F(name) PFN_vk##name name
typedef struct {
    VkCommandBuffer capture, copy[2];
    VkFence fences[3];
    int pending[3];
    VkSemaphore acquired[2];
    VkQueryPool queries;
    unsigned timed_mask;
} gpu_slot;
struct gfg_gpu_fg {
    VkDevice device;
    VkQueue queue;
    VkSwapchainKHR swapchain;
    VkExtent2D extent;
    VkImage *images;
    uint32_t image_count;
    VkSemaphore *real_ready, *generated_ready;
    VkCommandPool pool;
    gpu_slot ring[RING];
    te_device *engine;
    te_context *context;
    uint32_t source_slot, ring_slot;
    int history, disabled;
    uint64_t real_frames, submitted_outputs, present_handoffs, bypasses;
    uint32_t timestamp_bits;
    float timestamp_period_ns;
    double capture_gpu_ms, output_copy_gpu_ms;
    uint64_t capture_samples, output_copy_samples;
    F(CreateCommandPool); F(DestroyCommandPool); F(AllocateCommandBuffers);
    F(ResetCommandBuffer); F(BeginCommandBuffer); F(EndCommandBuffer);
    F(CreateSemaphore); F(DestroySemaphore); F(CreateFence); F(DestroyFence);
    F(GetFenceStatus); F(WaitForFences); F(ResetFences); F(QueueSubmit);
    F(CmdPipelineBarrier); F(CmdCopyImage); F(AcquireNextImageKHR);
    F(GetSwapchainImagesKHR); F(QueueWaitIdle);
    F(CreateQueryPool); F(DestroyQueryPool); F(GetQueryPoolResults);
    F(CmdResetQueryPool); F(CmdWriteTimestamp);
};

static int success(VkResult r) { return r == VK_SUCCESS || r == VK_SUBOPTIMAL_KHR; }
static VkImageMemoryBarrier image_barrier(VkImage image, VkImageLayout before,
        VkImageLayout after, VkAccessFlags src, VkAccessFlags dst) {
    VkImageMemoryBarrier b = {.sType=VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER,
        .srcAccessMask=src,.dstAccessMask=dst,.oldLayout=before,.newLayout=after,
        .srcQueueFamilyIndex=VK_QUEUE_FAMILY_IGNORED,.dstQueueFamilyIndex=VK_QUEUE_FAMILY_IGNORED,
        .image=image,.subresourceRange={VK_IMAGE_ASPECT_COLOR_BIT,0,1,0,1}};
    return b;
}
static int record_copy(gfg_gpu_fg *fg, VkCommandBuffer cb, VkImage source,
        VkImage dest, int capture, VkQueryPool queries, uint32_t query) {
    if (fg->ResetCommandBuffer(cb,0) != VK_SUCCESS) return 0;
    VkCommandBufferBeginInfo bi = {.sType=VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO,
        .flags=VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT};
    if (fg->BeginCommandBuffer(cb,&bi) != VK_SUCCESS) return 0;
    fg->CmdResetQueryPool(cb,queries,query,2);
    fg->CmdWriteTimestamp(cb,VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT,queries,query);
    VkImageMemoryBarrier before[2] = {
        image_barrier(source,capture?VK_IMAGE_LAYOUT_PRESENT_SRC_KHR:VK_IMAGE_LAYOUT_GENERAL,
            VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL,capture?0:VK_ACCESS_SHADER_WRITE_BIT,VK_ACCESS_TRANSFER_READ_BIT),
        image_barrier(dest,capture?VK_IMAGE_LAYOUT_GENERAL:VK_IMAGE_LAYOUT_UNDEFINED,
            VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL,capture?VK_ACCESS_SHADER_READ_BIT:0,VK_ACCESS_TRANSFER_WRITE_BIT)};
    fg->CmdPipelineBarrier(cb,VK_PIPELINE_STAGE_ALL_COMMANDS_BIT,VK_PIPELINE_STAGE_TRANSFER_BIT,
        0,0,NULL,0,NULL,2,before);
    VkImageCopy region = {.srcSubresource={VK_IMAGE_ASPECT_COLOR_BIT,0,0,1},
        .dstSubresource={VK_IMAGE_ASPECT_COLOR_BIT,0,0,1},
        .extent={fg->extent.width,fg->extent.height,1}};
    /* Compatible 32-bit formats copy encoded bytes; no blit gamma conversion. */
    fg->CmdCopyImage(cb,source,VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL,
        dest,VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL,1,&region);
    VkImageMemoryBarrier after[2] = {
        image_barrier(source,VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL,
            capture?VK_IMAGE_LAYOUT_PRESENT_SRC_KHR:VK_IMAGE_LAYOUT_GENERAL,
            VK_ACCESS_TRANSFER_READ_BIT,capture?0:VK_ACCESS_SHADER_WRITE_BIT),
        image_barrier(dest,VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL,
            capture?VK_IMAGE_LAYOUT_GENERAL:VK_IMAGE_LAYOUT_PRESENT_SRC_KHR,
            VK_ACCESS_TRANSFER_WRITE_BIT,capture?VK_ACCESS_SHADER_READ_BIT:0)};
    fg->CmdPipelineBarrier(cb,VK_PIPELINE_STAGE_TRANSFER_BIT,VK_PIPELINE_STAGE_ALL_COMMANDS_BIT,
        0,0,NULL,0,NULL,2,after);
    fg->CmdWriteTimestamp(cb,VK_PIPELINE_STAGE_BOTTOM_OF_PIPE_BIT,queries,query+1);
    return fg->EndCommandBuffer(cb) == VK_SUCCESS;
}
static VkResult submit(gfg_gpu_fg *fg, gpu_slot *slot, uint32_t which,
        VkCommandBuffer command, uint32_t wait_count, const VkSemaphore *waits,
        VkSemaphore signal) {
    VkPipelineStageFlags stages[MAX_WAITS];
    if (wait_count > MAX_WAITS) return VK_ERROR_INITIALIZATION_FAILED;
    for (uint32_t i=0;i<wait_count;++i) stages[i]=VK_PIPELINE_STAGE_ALL_COMMANDS_BIT;
    VkSubmitInfo si = {.sType=VK_STRUCTURE_TYPE_SUBMIT_INFO,
        .waitSemaphoreCount=wait_count,.pWaitSemaphores=waits,.pWaitDstStageMask=stages,
        .commandBufferCount=1,.pCommandBuffers=&command,
        .signalSemaphoreCount=1,.pSignalSemaphores=&signal};
    VkResult r=fg->ResetFences(fg->device,1,&slot->fences[which]);
    if (r==VK_SUCCESS) r=fg->QueueSubmit(fg->queue,1,&si,slot->fences[which]);
    if (r==VK_SUCCESS) {slot->pending[which]=1;slot->timed_mask|=1u<<which;}
    return r;
}
static void collect_transport(gfg_gpu_fg *fg, gpu_slot *slot) {
    const uint64_t mask=fg->timestamp_bits>=64?UINT64_MAX:((1ull<<fg->timestamp_bits)-1);
    for(uint32_t i=0;i<3;++i){
        if(!(slot->timed_mask&(1u<<i))) continue;
        uint64_t ticks[2];
        if(fg->GetQueryPoolResults(fg->device,slot->queries,i*2,2,sizeof(ticks),ticks,
            sizeof(uint64_t),VK_QUERY_RESULT_64_BIT)==VK_SUCCESS){
            double ms=(double)((ticks[1]-ticks[0])&mask)*(double)fg->timestamp_period_ns*1e-6;
            if(i){fg->output_copy_gpu_ms+=ms;++fg->output_copy_samples;}
            else {fg->capture_gpu_ms+=ms;++fg->capture_samples;}
        }
    }
    slot->timed_mask=0;
}
static int slot_ready(gfg_gpu_fg *fg, gpu_slot *slot) {
    for (uint32_t i=0;i<3;++i) {
        if (!slot->pending[i]) continue;
        if (fg->GetFenceStatus(fg->device,slot->fences[i]) != VK_SUCCESS) return 0;
        slot->pending[i]=0;
    }
    collect_transport(fg,slot);
    return 1;
}
static void statistics(gfg_gpu_fg *fg, int force) {
    if (!force && fg->real_frames%120 && !fg->disabled) return;
    te_poll(fg->context);
    te_pair_stats stats={0};
    uint64_t completed=te_last_stats(fg->context,&stats)==VK_SUCCESS?stats.outputs_completed_total:0;
    const double analysis=stats.timed ? stats.stage_ms[0]+stats.stage_ms[1]+stats.stage_ms[2] : -1.0;
    fprintf(stderr,"[gfg-native-gpu] real_calls=%llu submitted_outputs=%llu gpu_completed=%llu "
        "present_handoffs=%llu bypasses=%llu physical_display=unobserved cpu_pixel_bytes=0 "
        "capture_gpu_ms_mean=%.4f copy_gpu_ms_mean=%.4f capture_samples=%llu copy_samples=%llu "
        "pair_sequence=%llu analysis_gpu_ms_last=%.4f synth_1_gpu_ms_last=%.4f synth_2_gpu_ms_last=%.4f scene_cut_last=%u held_last=%d\n",
        (unsigned long long)fg->real_frames,(unsigned long long)fg->submitted_outputs,
        (unsigned long long)completed,(unsigned long long)fg->present_handoffs,
        (unsigned long long)fg->bypasses,
        fg->capture_samples?fg->capture_gpu_ms/(double)fg->capture_samples:-1.0,
        fg->output_copy_samples?fg->output_copy_gpu_ms/(double)fg->output_copy_samples:-1.0,
        (unsigned long long)fg->capture_samples,(unsigned long long)fg->output_copy_samples,
        (unsigned long long)stats.sequence,analysis,
        stats.timed && stats.outputs>0 ? stats.frame_ms[0][TE_FRAME_TOTAL] : -1.0,
        stats.timed && stats.outputs>1 ? stats.frame_ms[1][TE_FRAME_TOTAL] : -1.0,
        stats.scene_cut,stats.held);
}

gfg_gpu_fg *gfg_gpu_fg_create(VkInstance instance, PFN_vkGetInstanceProcAddr gipa, VkPhysicalDevice physical,
        VkDevice device, PFN_vkGetDeviceProcAddr gdpa, VkSwapchainKHR swapchain,
        VkExtent2D extent, VkFormat format, VkQueue queue, uint32_t family,
        PFN_vkSetDeviceLoaderData set_loader_data) {
    if(!set_loader_data) return NULL;
    if (format!=VK_FORMAT_R8G8B8A8_UNORM && format!=VK_FORMAT_R8G8B8A8_SRGB &&
        format!=VK_FORMAT_B8G8R8A8_UNORM && format!=VK_FORMAT_B8G8R8A8_SRGB) return NULL;
    gfg_gpu_fg *fg=calloc(1,sizeof(*fg));
    if (!fg) return NULL;
    fg->device=device;fg->queue=queue;fg->swapchain=swapchain;fg->extent=extent;
#define LOAD(name) do { fg->name=(PFN_vk##name)gdpa(device,"vk" #name); if(!fg->name) goto fail; } while(0)
    LOAD(CreateCommandPool);LOAD(DestroyCommandPool);LOAD(AllocateCommandBuffers);
    LOAD(ResetCommandBuffer);LOAD(BeginCommandBuffer);LOAD(EndCommandBuffer);
    LOAD(CreateSemaphore);LOAD(DestroySemaphore);LOAD(CreateFence);LOAD(DestroyFence);
    LOAD(GetFenceStatus);LOAD(WaitForFences);LOAD(ResetFences);LOAD(QueueSubmit);
    LOAD(CmdPipelineBarrier);LOAD(CmdCopyImage);LOAD(AcquireNextImageKHR);
    LOAD(GetSwapchainImagesKHR);LOAD(QueueWaitIdle);
    LOAD(CreateQueryPool);LOAD(DestroyQueryPool);LOAD(GetQueryPoolResults);
    LOAD(CmdResetQueryPool);LOAD(CmdWriteTimestamp);
#undef LOAD
    if (te_device_borrow(instance,gipa,physical,device,gdpa,set_loader_data,queue,family,&fg->engine)!=VK_SUCCESS) goto fail;
    te_device_timestamp_info(fg->engine,&fg->timestamp_bits,&fg->timestamp_period_ns);
    te_context_desc desc;
    te_context_desc_default(&desc,extent.width,extent.height,2);
    desc.source_bgra=desc.output_bgra=(format==VK_FORMAT_B8G8R8A8_UNORM || format==VK_FORMAT_B8G8R8A8_SRGB);
    desc.params.full_density=2;
    if (te_context_create(fg->engine,&desc,&fg->context)!=VK_SUCCESS) goto fail;
    if (fg->GetSwapchainImagesKHR(device,swapchain,&fg->image_count,NULL)!=VK_SUCCESS ||
        fg->image_count<3 || fg->image_count>256) goto fail;
    fg->images=calloc(fg->image_count,sizeof(*fg->images));
    fg->real_ready=calloc(fg->image_count,sizeof(*fg->real_ready));
    fg->generated_ready=calloc(fg->image_count,sizeof(*fg->generated_ready));
    if (!fg->images || !fg->real_ready || !fg->generated_ready) goto fail;
    if (fg->GetSwapchainImagesKHR(device,swapchain,&fg->image_count,fg->images)!=VK_SUCCESS) goto fail;
    VkSemaphoreCreateInfo sci={.sType=VK_STRUCTURE_TYPE_SEMAPHORE_CREATE_INFO};
    for (uint32_t i=0;i<fg->image_count;++i) {
        if (fg->CreateSemaphore(device,&sci,NULL,&fg->real_ready[i])!=VK_SUCCESS ||
            fg->CreateSemaphore(device,&sci,NULL,&fg->generated_ready[i])!=VK_SUCCESS) goto fail;
    }
    VkCommandPoolCreateInfo pci={.sType=VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO,
        .flags=VK_COMMAND_POOL_CREATE_RESET_COMMAND_BUFFER_BIT,.queueFamilyIndex=family};
    if(fg->CreateCommandPool(device,&pci,NULL,&fg->pool)!=VK_SUCCESS) goto fail;
    for(uint32_t i=0;i<RING;++i){
        gpu_slot *slot=&fg->ring[i];
        VkQueryPoolCreateInfo qci={.sType=VK_STRUCTURE_TYPE_QUERY_POOL_CREATE_INFO,
            .queryType=VK_QUERY_TYPE_TIMESTAMP,.queryCount=6};
        if(fg->CreateQueryPool(device,&qci,NULL,&slot->queries)!=VK_SUCCESS) goto fail;
        VkCommandBuffer buffers[3];
        VkCommandBufferAllocateInfo ai={.sType=VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO,
            .commandPool=fg->pool,.level=VK_COMMAND_BUFFER_LEVEL_PRIMARY,.commandBufferCount=3};
        if(fg->AllocateCommandBuffers(device,&ai,buffers)!=VK_SUCCESS) goto fail;
        for(uint32_t j=0;j<3;++j)
            if(set_loader_data(device,buffers[j])!=VK_SUCCESS) goto fail;
        slot->capture=buffers[0];slot->copy[0]=buffers[1];slot->copy[1]=buffers[2];
        VkFenceCreateInfo fci={.sType=VK_STRUCTURE_TYPE_FENCE_CREATE_INFO};
        for(uint32_t j=0;j<3;++j)
            if(fg->CreateFence(device,&fci,NULL,&slot->fences[j])!=VK_SUCCESS) goto fail;
        for(uint32_t j=0;j<2;++j)
            if(fg->CreateSemaphore(device,&sci,NULL,&slot->acquired[j])!=VK_SUCCESS) goto fail;
    }
    fprintf(stderr,"[gfg-native-gpu] initialized %ux%u multiplier=3 device=application "
        "source_bgra=%d cpu_pixel_bytes=0 algorithm=gpu-tiles\n",extent.width,extent.height,desc.source_bgra);
    return fg;
fail:
    fprintf(stderr,"[gfg-native-gpu] initialization refused: %s\n",te_last_error());
    gfg_gpu_fg_destroy(fg);
    return NULL;
}

VkResult gfg_gpu_fg_present(gfg_gpu_fg *fg, VkQueue queue, const VkPresentInfoKHR *original,
        PFN_vkQueuePresentKHR next_present) {
    ++fg->real_frames;
    if(queue!=fg->queue || fg->disabled || original->waitSemaphoreCount>MAX_WAITS ||
        original->pImageIndices[0]>=fg->image_count){
        fg->history=0;++fg->bypasses;
        return next_present(queue,original);
    }
    gpu_slot *slot=&fg->ring[fg->ring_slot];
    te_poll(fg->context);
    if(!slot_ready(fg,slot)){
        fg->history=0;++fg->bypasses;
        return next_present(fg->queue,original);
    }
    uint32_t real_index=original->pImageIndices[0];
    if(!record_copy(fg,slot->capture,fg->images[real_index],
            te_source_image(fg->context,fg->source_slot),1,slot->queries,0)){
        fg->disabled=1;
        return next_present(fg->queue,original);
    }
    VkResult r=submit(fg,slot,0,slot->capture,original->waitSemaphoreCount,
        original->pWaitSemaphores,fg->real_ready[real_index]);
    if(r!=VK_SUCCESS) return r; /* Failed submit: never replay ambiguous binary waits. */
    VkPresentInfoKHR real=*original;
    real.waitSemaphoreCount=1;real.pWaitSemaphores=&fg->real_ready[real_index];
    te_submit work={.slot=fg->source_slot,.count=fg->history?2u:0u,
        .timestamps={1.0f/3.0f,2.0f/3.0f},.nonblocking=1,.discontinuity=!fg->history};
    r=te_submit_frame(fg->context,&work);
    fg->source_slot^=1u;
    fg->ring_slot=(fg->ring_slot+1)%RING;
    if(r!=VK_SUCCESS){
        ++fg->bypasses;fg->history=0;
        if(r!=VK_NOT_READY) fg->disabled=1;
        return next_present(fg->queue,&real);
    }
    fg->submitted_outputs+=work.count;
    fg->history=1;
    for(uint32_t output=0;output<work.count;++output){
        uint32_t index=UINT32_MAX;
        r=fg->AcquireNextImageKHR(fg->device,fg->swapchain,0,slot->acquired[output],VK_NULL_HANDLE,&index);
        if(!success(r)){
            ++fg->bypasses;
            if(r!=VK_NOT_READY && r!=VK_TIMEOUT) fg->disabled=1;
            break;
        }
        if(index>=fg->image_count) return VK_ERROR_INITIALIZATION_FAILED;
        if(!record_copy(fg,slot->copy[output],te_output_image(fg->context,output),fg->images[index],0,slot->queries,(output+1)*2))
            return VK_ERROR_INITIALIZATION_FAILED;
        r=submit(fg,slot,output+1,slot->copy[output],1,&slot->acquired[output],fg->generated_ready[index]);
        if(r!=VK_SUCCESS) return r;
        VkPresentInfoKHR generated={.sType=VK_STRUCTURE_TYPE_PRESENT_INFO_KHR,
            .waitSemaphoreCount=1,.pWaitSemaphores=&fg->generated_ready[index],
            .swapchainCount=1,.pSwapchains=&fg->swapchain,.pImageIndices=&index};
        r=next_present(fg->queue,&generated);
        if(!success(r)){fg->disabled=1;break;}
        ++fg->present_handoffs;
    }
    r=next_present(fg->queue,&real);
    statistics(fg,0);
    return r;
}

void gfg_gpu_fg_reset(gfg_gpu_fg *fg) { if(fg) fg->history=0; }

void gfg_gpu_fg_destroy(gfg_gpu_fg *fg) {
    if(!fg) return;
    /* Retirement only; these calls are absent from the per-frame path. WSI
     * semaphore destruction also needs the application's presentation queue
     * drained. Display completion itself is not inferred from this wait. */
    if(fg->QueueWaitIdle && fg->pool) fg->QueueWaitIdle(fg->queue);
    if(fg->pool) for(uint32_t i=0;i<RING;++i)collect_transport(fg,&fg->ring[i]);
    if(fg->context) statistics(fg,1);
    te_context_destroy(fg->context);
    te_device_destroy(fg->engine);
    for(uint32_t i=0;i<RING;++i){
        if(fg->ring[i].queries) fg->DestroyQueryPool(fg->device,fg->ring[i].queries,NULL);
        for(uint32_t j=0;j<3;++j)
            if(fg->ring[i].fences[j]) fg->DestroyFence(fg->device,fg->ring[i].fences[j],NULL);
        for(uint32_t j=0;j<2;++j)
            if(fg->ring[i].acquired[j]) fg->DestroySemaphore(fg->device,fg->ring[i].acquired[j],NULL);
    }
    for(uint32_t i=0;i<fg->image_count;++i){
        if(fg->real_ready && fg->real_ready[i]) fg->DestroySemaphore(fg->device,fg->real_ready[i],NULL);
        if(fg->generated_ready && fg->generated_ready[i]) fg->DestroySemaphore(fg->device,fg->generated_ready[i],NULL);
    }
    if(fg->pool) fg->DestroyCommandPool(fg->device,fg->pool,NULL);
    free(fg->images);free(fg->real_ready);free(fg->generated_ready);free(fg);
}
