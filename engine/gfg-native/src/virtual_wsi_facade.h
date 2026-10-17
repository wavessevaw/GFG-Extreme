/* SPDX-License-Identifier: GPL-3.0-or-later
 * Vulkan WSI-shaped source proxy for the experimental single-output-owner.
 *
 * This is NOT an enabled Vulkan layer. It models the app-facing contract
 * independently of the visible compositor swapchain. Vulkan images belong
 * to the caller. A real layer must also intercept every applicable WSI
 * query/extension and implement format/pNext/oldSwapchain compatibility.
 */
#ifndef GFG_VIRTUAL_WSI_FACADE_H
#define GFG_VIRTUAL_WSI_FACADE_H
#include <vulkan/vulkan.h>
#include <stdint.h>
#include <string.h>
#include "virtual_source.h"

typedef VkResult (*gfg_vwsi_acquire_signal)(void *, VkSemaphore, VkFence);
typedef VkResult (*gfg_vwsi_copy_submit)(void *, uint32_t, uint64_t,
                        uint32_t, const VkSemaphore *);
typedef struct {
    gfg_virtual_source source;
    VkSwapchainKHR handle;
    VkImage images[GFG_VIRTUAL_MAX_IMAGES];
    VkFormat format;
    VkExtent2D extent;
    uint32_t accepts,copy_retirements,incorrect;
    void *user;
    gfg_vwsi_acquire_signal signal_acquire;
    gfg_vwsi_copy_submit copy_submit;
    int closed;
} gfg_virtual_wsi;

static inline VkResult gfg_vwsi_init(gfg_virtual_wsi *v,
                VkSwapchainKHR opaque_handle,const VkImage *images,
                uint32_t count,VkFormat format,VkExtent2D extent,
                void *user,gfg_vwsi_acquire_signal acquire_fn,
                gfg_vwsi_copy_submit copy_fn) {
    if(!v || !opaque_handle || !images || !count ||
       count>GFG_VIRTUAL_MAX_IMAGES || !extent.width || !extent.height ||
       !acquire_fn || !copy_fn)
        return VK_ERROR_INITIALIZATION_FAILED;
    memset(v,0,sizeof(*v));
    if(!gfg_virtual_init(&v->source,count))return VK_ERROR_INITIALIZATION_FAILED;
    for(uint32_t i=0;i<count;++i){
        if(!images[i])return VK_ERROR_INITIALIZATION_FAILED;
        v->images[i]=images[i];
    }
    v->handle=opaque_handle;v->format=format;v->extent=extent;
    v->user=user;v->signal_acquire=acquire_fn;v->copy_submit=copy_fn;
    return VK_SUCCESS;
}
static inline VkResult gfg_vwsi_get_images(gfg_virtual_wsi *v,
                 VkSwapchainKHR swapchain,uint32_t *count,VkImage *images) {
    if(!v||!count||v->closed||swapchain!=v->handle)
        return VK_ERROR_OUT_OF_DATE_KHR;
    const uint32_t available=v->source.count;
    if(!images) {*count=available;return VK_SUCCESS;}
    uint32_t provided=*count;
    uint32_t n=provided<available?provided:available;
    memcpy(images,v->images,(size_t)n*sizeof(VkImage));
    *count=n;
    return provided<available?VK_INCOMPLETE:VK_SUCCESS;
}
/* Acquire signalling is a GPU operation (e.g. an empty VkQueueSubmit).
 * Never host-signal Vulkan binary semaphores. On signalling failure, undo
 * acquisition so the game does not permanently lose an image. */
static inline VkResult gfg_vwsi_acquire(gfg_virtual_wsi *v,
           VkSwapchainKHR swapchain,uint64_t timeout,
           VkSemaphore semaphore,VkFence fence,uint32_t *index) {
    if(!v||!index||v->closed||swapchain!=v->handle)
        return VK_ERROR_OUT_OF_DATE_KHR;
    if(!semaphore && !fence)return VK_ERROR_INITIALIZATION_FAILED;
    unsigned idx=0;
    if(!gfg_virtual_acquire(&v->source,&idx))
        return timeout?VK_TIMEOUT:VK_NOT_READY;
    VkResult result=v->signal_acquire(v->user,semaphore,fence);
    if(result!=VK_SUCCESS) {
        gfg_virtual_cancel_acquire(&v->source,idx);
        return result;
    }
    *index=idx;
    return VK_SUCCESS;
}
/* Present is redirected to the CAPTURE queue, NOT the output swapchain.
 * The callback MUST submit a GPU copy waiting on the game's real render
 * semaphore(s). A successful callback owns those waits exactly once and
 * signals a copy fence. Release is permitted only after fence completion.
 * No second vkQueuePresentKHR may be issued for this source image.
 *
 * Subset: one virtual swapchain, no pNext (present id/fence, mode, etc.).
 * Fail closed BEFORE consuming semaphores on unknown extensions. */
static inline VkResult gfg_vwsi_present(gfg_virtual_wsi *v,
                     const VkPresentInfoKHR *info,uint64_t *ticket_out) {
    if(!v||!info||v->closed||!ticket_out ||
       info->sType!=VK_STRUCTURE_TYPE_PRESENT_INFO_KHR ||
       info->pNext || info->swapchainCount!=1 ||
       !info->pSwapchains || !info->pImageIndices ||
       info->pSwapchains[0]!=v->handle ||
       (info->waitSemaphoreCount && !info->pWaitSemaphores))
        return VK_ERROR_INITIALIZATION_FAILED;
    const uint32_t idx=info->pImageIndices[0];
    uint64_t ticket=0;
    if(!gfg_virtual_begin_snapshot(&v->source,idx,&ticket)) {
        ++v->incorrect;
        if(info->pResults)info->pResults[0]=VK_ERROR_INITIALIZATION_FAILED;
        return VK_ERROR_INITIALIZATION_FAILED;
    }
    /* If the callback failed after submitting a GPU copy, the handle
     * deliberately remains COPYING and must be resolved at teardown.
     * We cannot blindly replay or re-use its possibly-consumed waits. */
    VkResult r=v->copy_submit(v->user,idx,ticket,
                             info->waitSemaphoreCount,info->pWaitSemaphores);
    if(r!=VK_SUCCESS) {
        ++v->incorrect;
        if(info->pResults)info->pResults[0]=r;
        return r;
    }
    ++v->accepts;
    *ticket_out=ticket;
    if(info->pResults)info->pResults[0]=VK_SUCCESS;
    return VK_SUCCESS;
}
static inline VkResult gfg_vwsi_retire(gfg_virtual_wsi *v,
               uint32_t image,uint64_t ticket,int copy_fence_signalled) {
    if(!v||v->closed)return VK_ERROR_OUT_OF_DATE_KHR;
    if(!gfg_virtual_release(&v->source,image,ticket,copy_fence_signalled)) {
        return copy_fence_signalled?VK_ERROR_INITIALIZATION_FAILED:VK_NOT_READY;
    }
    ++v->copy_retirements;
    return VK_SUCCESS;
}
static inline void gfg_vwsi_close(gfg_virtual_wsi *v) {
    if(!v)return;
    v->closed=1;gfg_virtual_close(&v->source);
}
#endif
