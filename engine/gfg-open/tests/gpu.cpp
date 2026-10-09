// SPDX-License-Identifier: GPL-3.0-or-later
// Execute the released SPIR-V on Vulkan (CI: lavapipe), not a CPU imitation.
#include <vulkan/vulkan.h>
#include "../embedded.hpp"
#include <array>
#include <vector>
#include <cassert>
#include <cstring>
#include <cmath>
#include <iostream>
#include <algorithm>
#include <stdexcept>
#define VKCHECK(x) do{auto result=(x);if(result!=VK_SUCCESS)throw std::runtime_error(#x);}while(0)
struct Image {VkImage image;VkDeviceMemory memory;VkImageView view;void* map;VkSubresourceLayout layout;};
int main(){
 VkInstance instance;VkInstanceCreateInfo ic{VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO};
 VkApplicationInfo app{VK_STRUCTURE_TYPE_APPLICATION_INFO};app.apiVersion=VK_API_VERSION_1_1;ic.pApplicationInfo=&app;
 VKCHECK(vkCreateInstance(&ic,nullptr,&instance));
 uint32_t n=1;VkPhysicalDevice physical;VKCHECK(vkEnumeratePhysicalDevices(instance,&n,&physical));
 uint32_t count=0;vkGetPhysicalDeviceQueueFamilyProperties(physical,&count,nullptr);
 std::vector<VkQueueFamilyProperties> families(count);vkGetPhysicalDeviceQueueFamilyProperties(physical,&count,families.data());
 uint32_t family=0;while(!(families[family].queueFlags&VK_QUEUE_COMPUTE_BIT))++family;
 float priority=1;VkDeviceQueueCreateInfo qi{VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO};qi.queueFamilyIndex=family;qi.queueCount=1;qi.pQueuePriorities=&priority;
 VkPhysicalDeviceFeatures supported;vkGetPhysicalDeviceFeatures(physical,&supported);
 VkDeviceCreateInfo dc{VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO};dc.queueCreateInfoCount=1;dc.pQueueCreateInfos=&qi;dc.pEnabledFeatures=&supported;
 VkDevice device;VKCHECK(vkCreateDevice(physical,&dc,nullptr,&device));VkQueue queue;vkGetDeviceQueue(device,family,0,&queue);
 VkPhysicalDeviceMemoryProperties mp;vkGetPhysicalDeviceMemoryProperties(physical,&mp);
 auto alloc=[&](VkMemoryRequirements req){
  uint32_t i=0;for(;i<mp.memoryTypeCount;i++)if((req.memoryTypeBits&(1u<<i))&&(mp.memoryTypes[i].propertyFlags&(VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT|VK_MEMORY_PROPERTY_HOST_COHERENT_BIT))==(VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT|VK_MEMORY_PROPERTY_HOST_COHERENT_BIT))break;
  if(i==mp.memoryTypeCount)throw std::runtime_error("coherent test memory unavailable");
  VkMemoryAllocateInfo a{VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO};a.allocationSize=req.size;a.memoryTypeIndex=i;VkDeviceMemory m;VKCHECK(vkAllocateMemory(device,&a,nullptr,&m));return m;
 };
 auto image=[&](uint32_t w,uint32_t h,VkFormat format){
  Image r{};VkImageCreateInfo a{VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO};a.imageType=VK_IMAGE_TYPE_2D;a.format=format;a.extent={w,h,1};a.mipLevels=1;a.arrayLayers=1;a.samples=VK_SAMPLE_COUNT_1_BIT;a.tiling=VK_IMAGE_TILING_LINEAR;a.usage=VK_IMAGE_USAGE_STORAGE_BIT;a.initialLayout=VK_IMAGE_LAYOUT_PREINITIALIZED;
  VKCHECK(vkCreateImage(device,&a,nullptr,&r.image));VkMemoryRequirements req;vkGetImageMemoryRequirements(device,r.image,&req);r.memory=alloc(req);VKCHECK(vkBindImageMemory(device,r.image,r.memory,0));VKCHECK(vkMapMemory(device,r.memory,0,VK_WHOLE_SIZE,0,&r.map));
  VkImageSubresource sub{VK_IMAGE_ASPECT_COLOR_BIT,0,0};vkGetImageSubresourceLayout(device,r.image,&sub,&r.layout);
  VkImageViewCreateInfo v{VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO};v.image=r.image;v.viewType=VK_IMAGE_VIEW_TYPE_2D;v.format=format;v.subresourceRange={VK_IMAGE_ASPECT_COLOR_BIT,0,1,0,1};VKCHECK(vkCreateImageView(device,&v,nullptr,&r.view));return r;
 };
 constexpr uint32_t W=67,H=49,TW=(W+7)/8,TH=(H+7)/8;
 std::array<Image,7> images{image(W,H,VK_FORMAT_R8G8B8A8_UNORM),image(W,H,VK_FORMAT_R8G8B8A8_UNORM),
 image(TW,TH,VK_FORMAT_R32G32B32A32_SFLOAT),image(TW,TH,VK_FORMAT_R32G32B32A32_SFLOAT),
 image(TW,TH,VK_FORMAT_R32G32B32A32_SFLOAT),image(TW,TH,VK_FORMAT_R32G32B32A32_SFLOAT),image(W,H,VK_FORMAT_R8G8B8A8_UNORM)};
 VkBuffer buffer;VkBufferCreateInfo bc{VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO};bc.size=32;bc.usage=VK_BUFFER_USAGE_UNIFORM_BUFFER_BIT;VKCHECK(vkCreateBuffer(device,&bc,nullptr,&buffer));
 VkMemoryRequirements br;vkGetBufferMemoryRequirements(device,buffer,&br);auto bm=alloc(br);VKCHECK(vkBindBufferMemory(device,buffer,bm,0));void* params;VKCHECK(vkMapMemory(device,bm,0,VK_WHOLE_SIZE,0,&params));
 struct P{uint32_t size[4];float timing[4];}p{{W,H,TW,TH},{.5f,1,0,0}};memcpy(params,&p,32);
 std::array<VkDescriptorSetLayoutBinding,7> bindings{};
 bindings[0]={0,VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER,1,VK_SHADER_STAGE_COMPUTE_BIT,nullptr};
 for(uint32_t i=1;i<7;i++)bindings[i]={47+i,VK_DESCRIPTOR_TYPE_STORAGE_IMAGE,1,VK_SHADER_STAGE_COMPUTE_BIT,nullptr};
 VkDescriptorSetLayoutCreateInfo lc{VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO};lc.bindingCount=7;lc.pBindings=bindings.data();VkDescriptorSetLayout layout;VKCHECK(vkCreateDescriptorSetLayout(device,&lc,nullptr,&layout));
 VkPipelineLayoutCreateInfo pc{VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO};pc.setLayoutCount=1;pc.pSetLayouts=&layout;VkPipelineLayout pl;VKCHECK(vkCreatePipelineLayout(device,&pc,nullptr,&pl));
 auto pipeline=[&](auto& code){VkShaderModuleCreateInfo sc{VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO};sc.codeSize=code.size()*4;sc.pCode=code.data();VkShaderModule shader;VKCHECK(vkCreateShaderModule(device,&sc,nullptr,&shader));
 VkComputePipelineCreateInfo cp{VK_STRUCTURE_TYPE_COMPUTE_PIPELINE_CREATE_INFO};cp.stage={VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO};cp.stage.stage=VK_SHADER_STAGE_COMPUTE_BIT;cp.stage.module=shader;cp.stage.pName="main";cp.layout=pl;VkPipeline pipe;VKCHECK(vkCreateComputePipelines(device,0,1,&cp,nullptr,&pipe));vkDestroyShaderModule(device,shader,nullptr);return pipe;};
 std::array<VkPipeline,3> pipelines{pipeline(gfg::embedded::flow),pipeline(gfg::embedded::refine),pipeline(gfg::embedded::compose)};
 VkDescriptorPoolSize sizes[2]{{VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER,1},{VK_DESCRIPTOR_TYPE_STORAGE_IMAGE,6}};
 VkDescriptorPoolCreateInfo dp{VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO};dp.maxSets=1;dp.poolSizeCount=2;dp.pPoolSizes=sizes;VkDescriptorPool pool;VKCHECK(vkCreateDescriptorPool(device,&dp,nullptr,&pool));
 VkDescriptorSetAllocateInfo da{VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO};da.descriptorPool=pool;da.descriptorSetCount=1;da.pSetLayouts=&layout;VkDescriptorSet set;VKCHECK(vkAllocateDescriptorSets(device,&da,&set));
 VkCommandPoolCreateInfo cpc{VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO};cpc.queueFamilyIndex=family;cpc.flags=VK_COMMAND_POOL_CREATE_RESET_COMMAND_BUFFER_BIT;VkCommandPool cmdpool;VKCHECK(vkCreateCommandPool(device,&cpc,nullptr,&cmdpool));
 VkCommandBufferAllocateInfo ca{VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO};ca.commandPool=cmdpool;ca.level=VK_COMMAND_BUFFER_LEVEL_PRIMARY;ca.commandBufferCount=1;VkCommandBuffer cmd;VKCHECK(vkAllocateCommandBuffers(device,&ca,&cmd));
 bool first=true;
 auto dispatch=[&](int stage){
  std::array<uint32_t,6> order=stage==2?std::array<uint32_t,6>{0,1,4,5,6,3}:std::array<uint32_t,6>{0,1,2,3,4,5};
  VkDescriptorBufferInfo bi{buffer,0,32};std::array<VkDescriptorImageInfo,6> ii{};std::array<VkWriteDescriptorSet,7> writes{};
  writes[0]={VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET};writes[0].dstSet=set;writes[0].dstBinding=0;writes[0].descriptorCount=1;writes[0].descriptorType=VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER;writes[0].pBufferInfo=&bi;
  for(uint32_t i=0;i<6;i++){ii[i]={0,images[order[i]].view,VK_IMAGE_LAYOUT_GENERAL};writes[i+1]={VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET};auto& v=writes[i+1];v.dstSet=set;v.dstBinding=48+i;v.descriptorCount=1;v.descriptorType=VK_DESCRIPTOR_TYPE_STORAGE_IMAGE;v.pImageInfo=&ii[i];}
  vkUpdateDescriptorSets(device,7,writes.data(),0,nullptr);
  VKCHECK(vkResetCommandBuffer(cmd,0));VkCommandBufferBeginInfo begin{VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO};VKCHECK(vkBeginCommandBuffer(cmd,&begin));
  std::array<VkImageMemoryBarrier,7> barriers{};
  for(uint32_t i=0;i<7;i++){auto& b=barriers[i];b={VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER};b.srcAccessMask=VK_ACCESS_HOST_WRITE_BIT|VK_ACCESS_SHADER_WRITE_BIT;b.dstAccessMask=VK_ACCESS_SHADER_READ_BIT|VK_ACCESS_SHADER_WRITE_BIT;b.oldLayout=first?VK_IMAGE_LAYOUT_PREINITIALIZED:VK_IMAGE_LAYOUT_GENERAL;b.newLayout=VK_IMAGE_LAYOUT_GENERAL;b.srcQueueFamilyIndex=b.dstQueueFamilyIndex=VK_QUEUE_FAMILY_IGNORED;b.image=images[i].image;b.subresourceRange={VK_IMAGE_ASPECT_COLOR_BIT,0,1,0,1};}
  vkCmdPipelineBarrier(cmd,VK_PIPELINE_STAGE_HOST_BIT|VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,0,0,nullptr,0,nullptr,7,barriers.data());first=false;
  vkCmdBindPipeline(cmd,VK_PIPELINE_BIND_POINT_COMPUTE,pipelines[stage]);vkCmdBindDescriptorSets(cmd,VK_PIPELINE_BIND_POINT_COMPUTE,pl,0,1,&set,0,nullptr);
  vkCmdDispatch(cmd,((stage==2?W:TW)+7)/8,((stage==2?H:TH)+7)/8,1);
  VkMemoryBarrier read{VK_STRUCTURE_TYPE_MEMORY_BARRIER};read.srcAccessMask=VK_ACCESS_SHADER_WRITE_BIT;read.dstAccessMask=VK_ACCESS_HOST_READ_BIT;
  vkCmdPipelineBarrier(cmd,VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,VK_PIPELINE_STAGE_HOST_BIT,0,1,&read,0,nullptr,0,nullptr);
  VKCHECK(vkEndCommandBuffer(cmd));VkSubmitInfo submit{VK_STRUCTURE_TYPE_SUBMIT_INFO};submit.commandBufferCount=1;submit.pCommandBuffers=&cmd;VKCHECK(vkQueueSubmit(queue,1,&submit,0));VKCHECK(vkQueueWaitIdle(queue));
 };
 auto pixel=[&](int imageIndex,uint32_t x,uint32_t y){return static_cast<unsigned char*>(images[imageIndex].map)+images[imageIndex].layout.offset+y*images[imageIndex].layout.rowPitch+x*4;};
 auto fill=[&](int index,int shift,int cut){for(uint32_t y=0;y<H;y++)for(uint32_t x=0;x<W;x++){auto* q=pixel(index,x,y);int xx=int(x)-shift;unsigned char val=cut>=0?cut:static_cast<unsigned char>((xx*37+int(y)*53+xx*int(y)*7)&255);q[0]=q[1]=q[2]=val;q[3]=255;}};
 // Static identity, including odd dimensions and padded workgroups.
 fill(0,0,-1);fill(1,0,-1);dispatch(0);dispatch(1);dispatch(2);
 for(uint32_t y=0;y<H;y++)for(uint32_t x=0;x<W;x++)assert(memcmp(pixel(0,x,y),pixel(6,x,y),4)==0);
 // Bidirectional flow must find a known 2-pixel translation.
 fill(1,2,-1);dispatch(0);dispatch(1);
 auto* forward=reinterpret_cast<float*>(static_cast<unsigned char*>(images[4].map)+images[4].layout.offset+3*images[4].layout.rowPitch+3*16);
 assert(std::abs(forward[0]-2)<.1&&std::abs(forward[1])<.1);
 dispatch(2); // midpoint must match the one-pixel translated image centrally.
 int errors=0,total=0;for(uint32_t y=12;y<H-12;y++)for(uint32_t x=12;x<W-12;x++){total++;if(std::abs(int(pixel(6,x,y)[0])-int(pixel(0,x-1,y)[0]))>2)errors++;}
 assert(errors<total/10);
 // Scene discontinuity: no half-grey blend / stale temporal trails.
 fill(0,0,0);fill(1,0,255);dispatch(0);dispatch(1);dispatch(2);
 for(uint32_t y=0;y<H;y++)for(uint32_t x=0;x<W;x++)assert(pixel(6,x,y)[0]==255);
 // Initial history invalid: output must be current real frame.
 p.timing[1]=0;memcpy(params,&p,32);fill(0,0,-1);fill(1,0,17);dispatch(0);dispatch(1);dispatch(2);
 for(uint32_t y=0;y<H;y++)for(uint32_t x=0;x<W;x++)assert(pixel(6,x,y)[0]==17);
 std::cout<<"GPU PASS: static, translation, scene-cut, initial history, odd extent\n";
 vkDeviceWaitIdle(device);vkDestroyCommandPool(device,cmdpool,nullptr);vkDestroyDescriptorPool(device,pool,nullptr);
 for(auto pipe:pipelines)vkDestroyPipeline(device,pipe,nullptr);vkDestroyPipelineLayout(device,pl,nullptr);vkDestroyDescriptorSetLayout(device,layout,nullptr);
 vkUnmapMemory(device,bm);vkDestroyBuffer(device,buffer,nullptr);vkFreeMemory(device,bm,nullptr);
 for(auto& i:images){vkUnmapMemory(device,i.memory);vkDestroyImageView(device,i.view,nullptr);vkDestroyImage(device,i.image,nullptr);vkFreeMemory(device,i.memory,nullptr);}
 vkDestroyDevice(device,nullptr);vkDestroyInstance(instance,nullptr);
}
