/* SPDX-License-Identifier: GPL-3.0-or-later
 * Test-only REAL Vulkan layer dispatch hooks for one controlled virtual
 * source swapchain. No loader is installed, and no production path is on.
 */
#define _GNU_SOURCE
#define GFG_NATIVE_TEST_OUTPUT_OWNER_HOOKS
#include "../src/layer.c"
#include <assert.h>
#include <stdio.h>
static unsigned downstream_images,downstream_acquires,downstream_presents;
static uint64_t last_snapshot_ticket;
static unsigned last_snapshot_image;
static unsigned acquire_signalled,game_wait_consumed;
static VkSwapchainKHR output_handle,app_handle;
static VkResult VKAPI_CALL stub_get_images(VkDevice d,VkSwapchainKHR sc,
                                           uint32_t *n,VkImage *out) {
    (void)d;assert(sc==output_handle);
    ++downstream_images;
    if(!out){*n=2;return VK_SUCCESS;}
    if(*n<2){*n=1;out[0]=(VkImage)(uintptr_t)0xFACE;return VK_INCOMPLETE;}
    out[0]=(VkImage)(uintptr_t)0xFACE;
    out[1]=(VkImage)(uintptr_t)0xFEED;
    *n=2;return VK_SUCCESS;
}
static VkResult VKAPI_CALL stub_acquire(VkDevice d,VkSwapchainKHR sc,
                      uint64_t timeout,VkSemaphore s,VkFence f,uint32_t *index) {
    (void)d;(void)timeout;(void)s;(void)f;
    assert(sc==output_handle);
    ++downstream_acquires;*index=0;return VK_SUCCESS;
}
static VkResult VKAPI_CALL stub_acquire2(VkDevice d,
                 const VkAcquireNextImageInfoKHR *a,uint32_t *index) {
    return stub_acquire(d,a->swapchain,a->timeout,a->semaphore,a->fence,index);
}
static VkResult VKAPI_CALL stub_present(VkQueue q,const VkPresentInfoKHR *p) {
    (void)q;assert(p&&p->swapchainCount==1&&p->pSwapchains[0]==output_handle);
    ++downstream_presents;return VK_SUCCESS;
}
static VkResult stub_signal(void *u,VkSemaphore sem,VkFence fence) {
    (void)u;assert(sem||fence);++acquire_signalled;return VK_SUCCESS;
}
static VkResult stub_snapshot(void *u,uint32_t image,uint64_t ticket,
                                uint32_t waits,const VkSemaphore *sems) {
    (void)u;assert(ticket&&waits==1&&sems&&sems[0]);
    ++game_wait_consumed;last_snapshot_image=image;last_snapshot_ticket=ticket;
    return VK_SUCCESS;
}
int main(void) {
    void *key=(void *)(uintptr_t)0xAEAB;
    VkDevice device=(VkDevice)&key;
    VkQueue queue=(VkQueue)&key;
    native_device d={0};
    d.key=key;d.handle=device;d.get_images=stub_get_images;
    d.acquire=stub_acquire;d.acquire2=stub_acquire2;
    d.present=stub_present;
    assert(!pthread_mutex_init(&d.lock,NULL));
    assert(!pthread_mutex_init(&d.queue_lock,NULL));
    devices=&d;
    app_handle=(VkSwapchainKHR)(uintptr_t)0xA123;
    output_handle=(VkSwapchainKHR)(uintptr_t)0xB456;
    const VkImage app_images[2]={
        (VkImage)(uintptr_t)0xAABB,
        (VkImage)(uintptr_t)0xCCDD
    };
    gfg_virtual_wsi virtual={0};
    assert(gfg_vwsi_init(&virtual,app_handle,app_images,2,
           VK_FORMAT_B8G8R8A8_UNORM,(VkExtent2D){1280,800},NULL,
           stub_signal,stub_snapshot)==VK_SUCCESS);
    native_swapchain app_sc={.handle=app_handle,.virtual_app=&virtual};
    d.swapchains=&app_sc;
    PFN_vkGetSwapchainImagesKHR get_images=(PFN_vkGetSwapchainImagesKHR)
        native_gdpa(device,"vkGetSwapchainImagesKHR");
    PFN_vkAcquireNextImageKHR acquire=(PFN_vkAcquireNextImageKHR)
        native_gdpa(device,"vkAcquireNextImageKHR");
    PFN_vkAcquireNextImage2KHR acquire2=(PFN_vkAcquireNextImage2KHR)
        native_gdpa(device,"vkAcquireNextImage2KHR");
    PFN_vkQueuePresentKHR present=(PFN_vkQueuePresentKHR)
        native_gdpa(device,"vkQueuePresentKHR");
    assert(get_images&&acquire&&acquire2&&present);
    assert(native_gipa((VkInstance)&key,"vkGetSwapchainImagesKHR")==
           (PFN_vkVoidFunction)get_images);
    assert(native_gipa((VkInstance)&key,"vkAcquireNextImageKHR")==
           (PFN_vkVoidFunction)acquire);
    assert(native_gipa((VkInstance)&key,"vkQueuePresentKHR")==
           (PFN_vkVoidFunction)present);
    uint32_t count=0;
    assert(get_images(device,app_handle,&count,NULL)==VK_SUCCESS&&count==2);
    VkImage images[2]={0};count=2;
    assert(get_images(device,app_handle,&count,images)==VK_SUCCESS);
    assert(images[0]==app_images[0]&&images[1]==app_images[1]);
    assert(downstream_images==0);

    uint32_t a=999,b=999,c=999;
    VkSemaphore acquire_sem=(VkSemaphore)(uintptr_t)0xFA10;
    assert(acquire(device,app_handle,0,acquire_sem,VK_NULL_HANDLE,&a)==VK_SUCCESS);
    VkAcquireNextImageInfoKHR args={.sType=VK_STRUCTURE_TYPE_ACQUIRE_NEXT_IMAGE_INFO_KHR,
        .swapchain=app_handle,.timeout=0,
        .semaphore=(VkSemaphore)(uintptr_t)0xFA20,.deviceMask=1};
    assert(acquire2(device,&args,&b)==VK_SUCCESS);
    assert(a!=b&&acquire_signalled==2&&downstream_acquires==0);
    assert(acquire(device,app_handle,0,acquire_sem,VK_NULL_HANDLE,&c)==VK_NOT_READY);

    VkSemaphore gpu_done=(VkSemaphore)(uintptr_t)0xFA30;
    VkResult per_swapchain=VK_ERROR_UNKNOWN;
    VkPresentInfoKHR p={.sType=VK_STRUCTURE_TYPE_PRESENT_INFO_KHR,
        .waitSemaphoreCount=1,.pWaitSemaphores=&gpu_done,
        .swapchainCount=1,.pSwapchains=&app_handle,
        .pImageIndices=&a,.pResults=&per_swapchain};
    assert(present(queue,&p)==VK_SUCCESS&&per_swapchain==VK_SUCCESS);
    assert(game_wait_consumed==1&&downstream_presents==0);
    assert(last_snapshot_image==a&&last_snapshot_ticket>0);
    assert(gfg_vwsi_retire(&virtual,a,last_snapshot_ticket,0)==VK_NOT_READY);
    assert(gfg_vwsi_retire(&virtual,a,last_snapshot_ticket,1)==VK_SUCCESS);
    assert(acquire(device,app_handle,0,acquire_sem,VK_NULL_HANDLE,&c)==VK_SUCCESS);
    assert(c==a);

    /* A normal downstream output swapchain is still passed through. */
    count=0;
    assert(get_images(device,output_handle,&count,NULL)==VK_SUCCESS&&count==2);
    assert(downstream_images==1);
    assert(acquire(device,output_handle,0,acquire_sem,VK_NULL_HANDLE,&c)==VK_SUCCESS);
    assert(downstream_acquires==1);
    p.pSwapchains=&output_handle;
    assert(present(queue,&p)==VK_SUCCESS&&downstream_presents==1);
    assert(game_wait_consumed==1); /* never consume waits a second time */

    gfg_vwsi_close(&virtual);gfg_vwsi_fini(&virtual);
    devices=NULL;pthread_mutex_destroy(&d.lock);pthread_mutex_destroy(&d.queue_lock);
    puts("GFG test layer: GIPA/GDPA->GetImages/Acquire/Acquire2/Present virtual source, separate output PASS");
    return 0;
}
