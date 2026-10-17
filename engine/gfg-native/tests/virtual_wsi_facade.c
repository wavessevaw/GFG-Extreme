/* SPDX-License-Identifier: GPL-3.0-or-later
 * API-shaped virtual WSI proxy: this does not hook a real game's Vulkan
 * calls. It verifies acquire signalled, source-present redirected into
 * snapshot and original image returned without output WSI involvement.
 */
#include "../src/virtual_wsi_facade.h"
#include <assert.h>
#include <stdio.h>
#include <stdint.h>
typedef struct {
    uint64_t signalled,captured,consumed,fail_acquire,fail_copy;
    uint32_t last_index;
} fake_gpu;
static VkResult acquire_gpu(void *arg,VkSemaphore s,VkFence f) {
    fake_gpu *g=arg;
    assert(s||f);
    if(g->fail_acquire)return VK_ERROR_DEVICE_LOST;
    ++g->signalled;
    return VK_SUCCESS;
}
static VkResult copy_gpu(void *arg,uint32_t index,uint64_t token,
                       uint32_t n,const VkSemaphore *sem) {
    fake_gpu *g=arg;
    assert(token && n==1 && sem && sem[0]);
    if(g->fail_copy)return VK_ERROR_DEVICE_LOST;
    ++g->captured;g->consumed+=n;g->last_index=index;
    return VK_SUCCESS;
}
static VkImage fake_image(uint64_t id) { return (VkImage)(uintptr_t)id; }
static VkSwapchainKHR fake_swapchain(uint64_t id) {
    return (VkSwapchainKHR)(uintptr_t)id;
}
static VkSemaphore fake_semaphore(uint64_t id) {
    return (VkSemaphore)(uintptr_t)id;
}
static void no_reused_source_before_gpu_copy(void) {
    gfg_virtual_wsi v;fake_gpu gpu={0};
    VkImage source[]={fake_image(0x201),fake_image(0x202)};
    VkSwapchainKHR handle=fake_swapchain(0x157);
    assert(gfg_vwsi_init(&v,handle,source,2,VK_FORMAT_B8G8R8A8_UNORM,
        (VkExtent2D){1280,800},&gpu,acquire_gpu,copy_gpu)==VK_SUCCESS);
    uint32_t count=0;assert(gfg_vwsi_get_images(&v,handle,&count,NULL)==VK_SUCCESS);
    assert(count==2);
    VkImage only=VK_NULL_HANDLE;count=1;
    assert(gfg_vwsi_get_images(&v,handle,&count,&only)==VK_INCOMPLETE);
    assert(only==source[0] && count==1);
    VkImage list[2]={0};count=2;
    assert(gfg_vwsi_get_images(&v,handle,&count,list)==VK_SUCCESS);
    assert(count==2 && list[0]==source[0] && list[1]==source[1]);
    uint32_t a=999,b=999,c=999;uint64_t ta=0,tb=0,tc=0;
    assert(gfg_vwsi_acquire(&v,handle,0,fake_semaphore(1),VK_NULL_HANDLE,&a)==VK_SUCCESS);
    assert(gfg_vwsi_acquire(&v,handle,0,fake_semaphore(2),VK_NULL_HANDLE,&b)==VK_SUCCESS);
    assert(a!=b && gpu.signalled==2);
    assert(gfg_vwsi_acquire(&v,handle,0,fake_semaphore(3),VK_NULL_HANDLE,&c)==VK_NOT_READY);
    assert(gfg_vwsi_acquire(&v,handle,1,fake_semaphore(3),VK_NULL_HANDLE,&c)==VK_TIMEOUT);
    assert(gfg_vwsi_acquire(&v,handle,0,VK_NULL_HANDLE,VK_NULL_HANDLE,&c)==VK_ERROR_INITIALIZATION_FAILED);
    VkResult result=VK_ERROR_UNKNOWN;
    VkSemaphore waits[1]={fake_semaphore(10)};
    VkPresentInfoKHR pi={.sType=VK_STRUCTURE_TYPE_PRESENT_INFO_KHR,
        .waitSemaphoreCount=1,.pWaitSemaphores=waits,
        .swapchainCount=1,.pSwapchains=&handle,.pImageIndices=&a,
        .pResults=&result};
    assert(gfg_vwsi_present(&v,&pi,&ta)==VK_SUCCESS);
    assert(result==VK_SUCCESS && ta && gpu.captured==1 && gpu.consumed==1);
    /* copy not done: source must remain unavailable */
    assert(gfg_vwsi_retire(&v,a,ta,0)==VK_NOT_READY);
    assert(gfg_vwsi_acquire(&v,handle,0,fake_semaphore(3),VK_NULL_HANDLE,&c)==VK_NOT_READY);
    assert(gfg_vwsi_retire(&v,a,ta+1,1)==VK_ERROR_INITIALIZATION_FAILED);
    assert(gfg_vwsi_retire(&v,a,ta,1)==VK_SUCCESS);
    assert(gfg_vwsi_acquire(&v,handle,0,fake_semaphore(3),VK_NULL_HANDLE,&c)==VK_SUCCESS);
    assert(c==a);
    pi.pImageIndices=&b;result=VK_ERROR_UNKNOWN;
    assert(gfg_vwsi_present(&v,&pi,&tb)==VK_SUCCESS && tb>ta);
    assert(gfg_vwsi_retire(&v,b,tb,1)==VK_SUCCESS);
    pi.pImageIndices=&c;result=VK_ERROR_UNKNOWN;
    assert(gfg_vwsi_present(&v,&pi,&tc)==VK_SUCCESS && tc>tb);
    assert(gfg_vwsi_retire(&v,c,tc,1)==VK_SUCCESS);
    assert(v.accepts==3 && v.copy_retirements==3 && gpu.signalled==3);
    assert(gpu.captured==3 && gpu.consumed==3);
    assert(gfg_virtual_all_idle(&v.source));
    gfg_vwsi_close(&v);
    assert(gfg_vwsi_acquire(&v,handle,0,fake_semaphore(4),VK_NULL_HANDLE,&c)==VK_ERROR_OUT_OF_DATE_KHR);
    puts("virtual WSI: two acquired, copy-fence gated release, exact wait ownership PASS");
}
static void unsupported_present_must_not_consume_waits(void) {
    gfg_virtual_wsi v;fake_gpu gpu={0};
    VkImage images[]={fake_image(0x501)};
    VkSwapchainKHR handle=fake_swapchain(0x503);
    assert(gfg_vwsi_init(&v,handle,images,1,VK_FORMAT_R8G8B8A8_UNORM,
        (VkExtent2D){640,480},&gpu,acquire_gpu,copy_gpu)==VK_SUCCESS);
    uint32_t image=999;uint64_t ticket=0;
    gpu.fail_acquire=1;
    assert(gfg_vwsi_acquire(&v,handle,0,fake_semaphore(31),VK_NULL_HANDLE,&image)==VK_ERROR_DEVICE_LOST);
    gpu.fail_acquire=0;
    assert(gfg_vwsi_acquire(&v,handle,0,fake_semaphore(32),VK_NULL_HANDLE,&image)==VK_SUCCESS);
    VkSemaphore wait=fake_semaphore(42);VkResult result=VK_ERROR_UNKNOWN;
    VkPresentInfoKHR p={.sType=VK_STRUCTURE_TYPE_PRESENT_INFO_KHR,
        .waitSemaphoreCount=1,.pWaitSemaphores=&wait,
        .swapchainCount=1,.pSwapchains=&handle,.pImageIndices=&image,.pResults=&result};
    VkBaseInStructure extension={.sType=(VkStructureType)1999912345};
    p.pNext=&extension;
    assert(gfg_vwsi_present(&v,&p,&ticket)==VK_ERROR_INITIALIZATION_FAILED);
    assert(gpu.consumed==0 && !v.accepts && v.source.state[image]==GFG_VIRTUAL_ACQUIRED);
    p.pNext=NULL;gpu.fail_copy=1;
    assert(gfg_vwsi_present(&v,&p,&ticket)==VK_ERROR_DEVICE_LOST);
    assert(!v.accepts && v.source.state[image]==GFG_VIRTUAL_COPYING);
    /* Important: unknown GPU completion stays quarantined, no release. */
    assert(gfg_vwsi_acquire(&v,handle,0,fake_semaphore(33),VK_NULL_HANDLE,&image)==VK_NOT_READY);
    assert(gfg_virtual_cancel_acquire(&v.source,image)==0);
    gfg_vwsi_close(&v);
    puts("virtual WSI: no semaphore replay, unsupported pNext refuses safely PASS");
}
int main(void) {
    no_reused_source_before_gpu_copy();
    unsupported_present_must_not_consume_waits();
    return 0;
}
