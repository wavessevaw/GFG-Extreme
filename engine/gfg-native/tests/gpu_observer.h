/* SPDX-License-Identifier: GPL-3.0-or-later
 * TEST ONLY: independent GPU copies inspect each image before lower WSI
 * presentation. CPU waits/readback here are deliberately outside the runtime.
 * This proves image content and API handoff order, never physical scanout.
 */
#include "gpu_bridge.h"
#include <math.h>
static struct {
    VkDevice device;
    VkQueue queue;
    VkImage *images;
    VkExtent2D extent;
    VkBuffer buffer;
    VkDeviceMemory memory;
    unsigned char *mapped;
    VkCommandPool pool;
    VkCommandBuffer command;
    VkFence fence;
    VkSemaphore *ready;
    uint32_t image_count, frame, interval_calls, total_calls, generated;
    unsigned char previous[4], samples[2][4];
    PFN_vkQueuePresentKHR lower;
    gfg_gpu_fg *fg;
    int failed;
} observer;
static VKAPI_ATTR VkResult VKAPI_CALL observer_loader_data(VkDevice device,void *object) {
    (void)device;(void)object;return VK_SUCCESS; /* top-level loader allocated these */
}
static VkResult observer_present(VkQueue queue,const VkPresentInfoKHR *info) {
    uint32_t index=info->pImageIndices[0];
    if(index>=observer.image_count) return VK_ERROR_INITIALIZATION_FAILED;
    vkResetCommandBuffer(observer.command,0);
    VkCommandBufferBeginInfo bi={.sType=VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO};
    if(vkBeginCommandBuffer(observer.command,&bi)!=VK_SUCCESS) return VK_ERROR_INITIALIZATION_FAILED;
    VkImageMemoryBarrier before={.sType=VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER,
        .oldLayout=VK_IMAGE_LAYOUT_PRESENT_SRC_KHR,.newLayout=VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL,
        .dstAccessMask=VK_ACCESS_TRANSFER_READ_BIT,
        .srcQueueFamilyIndex=VK_QUEUE_FAMILY_IGNORED,.dstQueueFamilyIndex=VK_QUEUE_FAMILY_IGNORED,
        .image=observer.images[index],.subresourceRange={VK_IMAGE_ASPECT_COLOR_BIT,0,1,0,1}};
    vkCmdPipelineBarrier(observer.command,VK_PIPELINE_STAGE_ALL_COMMANDS_BIT,VK_PIPELINE_STAGE_TRANSFER_BIT,
        0,0,NULL,0,NULL,1,&before);
    VkBufferImageCopy region={.imageSubresource={VK_IMAGE_ASPECT_COLOR_BIT,0,0,1},
        .imageExtent={observer.extent.width,observer.extent.height,1}};
    vkCmdCopyImageToBuffer(observer.command,observer.images[index],VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL,
        observer.buffer,1,&region);
    VkImageMemoryBarrier after=before;
    after.oldLayout=VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL;after.newLayout=VK_IMAGE_LAYOUT_PRESENT_SRC_KHR;
    after.srcAccessMask=VK_ACCESS_TRANSFER_READ_BIT;after.dstAccessMask=0;
    VkBufferMemoryBarrier host={.sType=VK_STRUCTURE_TYPE_BUFFER_MEMORY_BARRIER,
        .srcAccessMask=VK_ACCESS_TRANSFER_WRITE_BIT,.dstAccessMask=VK_ACCESS_HOST_READ_BIT,
        .srcQueueFamilyIndex=VK_QUEUE_FAMILY_IGNORED,.dstQueueFamilyIndex=VK_QUEUE_FAMILY_IGNORED,
        .buffer=observer.buffer,.offset=0,.size=VK_WHOLE_SIZE};
    vkCmdPipelineBarrier(observer.command,VK_PIPELINE_STAGE_TRANSFER_BIT,
        VK_PIPELINE_STAGE_HOST_BIT|VK_PIPELINE_STAGE_BOTTOM_OF_PIPE_BIT,0,0,NULL,1,&host,1,&after);
    if(vkEndCommandBuffer(observer.command)!=VK_SUCCESS) return VK_ERROR_INITIALIZATION_FAILED;
    VkPipelineStageFlags stages[64];
    if(info->waitSemaphoreCount>64) return VK_ERROR_INITIALIZATION_FAILED;
    for(uint32_t i=0;i<info->waitSemaphoreCount;++i) stages[i]=VK_PIPELINE_STAGE_ALL_COMMANDS_BIT;
    VkSubmitInfo submit={.sType=VK_STRUCTURE_TYPE_SUBMIT_INFO,
        .waitSemaphoreCount=info->waitSemaphoreCount,.pWaitSemaphores=info->pWaitSemaphores,.pWaitDstStageMask=stages,
        .commandBufferCount=1,.pCommandBuffers=&observer.command,
        .signalSemaphoreCount=1,.pSignalSemaphores=&observer.ready[index]};
    vkResetFences(observer.device,1,&observer.fence);
    VkResult r=vkQueueSubmit(queue,1,&submit,observer.fence);
    if(r!=VK_SUCCESS) return r;
    r=vkWaitForFences(observer.device,1,&observer.fence,VK_TRUE,UINT64_MAX);
    if(r!=VK_SUCCESS) return r;
    for(size_t pixel=0;pixel<(size_t)observer.extent.width*observer.extent.height;++pixel)
        for(unsigned c=0;c<3;++c)
            if(abs((int)observer.mapped[4*pixel+c]-(int)observer.mapped[c])>1) observer.failed=1;
    if(observer.frame && observer.interval_calls<2){
        memcpy(observer.samples[observer.interval_calls],observer.mapped,4);
        ++observer.generated;
    }else{
        if(observer.frame){
            for(uint32_t output=0;output<2;++output){
                for(uint32_t c=0;c<3;++c){
                    int expected=((2-(int)output)*(int)observer.previous[c]+(1+(int)output)*(int)observer.mapped[c]+1)/3;
                    if(abs((int)observer.samples[output][c]-expected)>2) observer.failed=1;
                }
                if(!memcmp(observer.samples[output],observer.previous,3) ||
                   !memcmp(observer.samples[output],observer.mapped,3)) observer.failed=1;
            }
        }
        memcpy(observer.previous,observer.mapped,4);
    }
    ++observer.interval_calls;++observer.total_calls;
    VkPresentInfoKHR wrapped=*info;
    wrapped.waitSemaphoreCount=1;wrapped.pWaitSemaphores=&observer.ready[index];
    return observer.lower(queue,&wrapped);
}
static int observer_start(VkInstance instance,VkPhysicalDevice physical,VkDevice device,
        VkQueue queue,VkSwapchainKHR swapchain,VkExtent2D extent,VkFormat format,
        VkImage *images,uint32_t count,uint32_t family,PFN_vkQueuePresentKHR lower){
    observer.device=device;observer.queue=queue;observer.images=images;
    observer.image_count=count;observer.extent=extent;observer.lower=lower;
    VkBufferCreateInfo bci={.sType=VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO,
        .size=(VkDeviceSize)extent.width*extent.height*4,
        .usage=VK_BUFFER_USAGE_TRANSFER_DST_BIT,.sharingMode=VK_SHARING_MODE_EXCLUSIVE};
    if(vkCreateBuffer(device,&bci,NULL,&observer.buffer)!=VK_SUCCESS) return 0;
    VkMemoryRequirements req;vkGetBufferMemoryRequirements(device,observer.buffer,&req);
    VkPhysicalDeviceMemoryProperties memory;vkGetPhysicalDeviceMemoryProperties(physical,&memory);
    uint32_t type=UINT32_MAX;
    for(uint32_t i=0;i<memory.memoryTypeCount;++i)
        if((req.memoryTypeBits&(1u<<i)) && (memory.memoryTypes[i].propertyFlags&
            (VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT|VK_MEMORY_PROPERTY_HOST_COHERENT_BIT))==
            (VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT|VK_MEMORY_PROPERTY_HOST_COHERENT_BIT)){type=i;break;}
    if(type==UINT32_MAX) return 0;
    VkMemoryAllocateInfo mai={.sType=VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO,.allocationSize=req.size,.memoryTypeIndex=type};
    if(vkAllocateMemory(device,&mai,NULL,&observer.memory)!=VK_SUCCESS ||
       vkBindBufferMemory(device,observer.buffer,observer.memory,0)!=VK_SUCCESS ||
       vkMapMemory(device,observer.memory,0,VK_WHOLE_SIZE,0,(void **)&observer.mapped)!=VK_SUCCESS) return 0;
    VkCommandPoolCreateInfo pci={.sType=VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO,
        .flags=VK_COMMAND_POOL_CREATE_RESET_COMMAND_BUFFER_BIT,.queueFamilyIndex=family};
    if(vkCreateCommandPool(device,&pci,NULL,&observer.pool)!=VK_SUCCESS) return 0;
    VkCommandBufferAllocateInfo ai={.sType=VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO,
        .commandPool=observer.pool,.level=VK_COMMAND_BUFFER_LEVEL_PRIMARY,.commandBufferCount=1};
    if(vkAllocateCommandBuffers(device,&ai,&observer.command)!=VK_SUCCESS) return 0;
    VkFenceCreateInfo fci={.sType=VK_STRUCTURE_TYPE_FENCE_CREATE_INFO};
    if(vkCreateFence(device,&fci,NULL,&observer.fence)!=VK_SUCCESS) return 0;
    observer.ready=calloc(count,sizeof(*observer.ready));if(!observer.ready) return 0;
    VkSemaphoreCreateInfo sci={.sType=VK_STRUCTURE_TYPE_SEMAPHORE_CREATE_INFO};
    for(uint32_t i=0;i<count;++i)
        if(vkCreateSemaphore(device,&sci,NULL,&observer.ready[i])!=VK_SUCCESS) return 0;
    observer.fg=gfg_gpu_fg_create(instance,vkGetInstanceProcAddr,physical,device,vkGetDeviceProcAddr,
        swapchain,extent,format,queue,family,observer_loader_data);
    return observer.fg!=NULL;
}
static int observer_finish(void){
    int passed=!observer.failed && observer.total_calls==10 && observer.generated==6;
    gfg_gpu_fg_destroy(observer.fg);
    for(uint32_t i=0;i<observer.image_count;++i)vkDestroySemaphore(observer.device,observer.ready[i],NULL);
    free(observer.ready);vkDestroyFence(observer.device,observer.fence,NULL);
    vkDestroyCommandPool(observer.device,observer.pool,NULL);
    vkUnmapMemory(observer.device,observer.memory);
    vkDestroyBuffer(observer.device,observer.buffer,NULL);vkFreeMemory(observer.device,observer.memory,NULL);
    fprintf(stderr,"GPU WSI observer: real=4 synthetic=6 content=%s handoff_order=%s physical_scanout=unobserved\n",
        passed?"PASS":"FAIL",observer.total_calls==10?"PASS":"FAIL");
    return passed;
}
