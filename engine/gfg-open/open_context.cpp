// SPDX-License-Identifier: GPL-3.0-or-later
#include "open_context.hpp"
#include "embedded.hpp"
#include <cmath>
#include <iostream>
#include <stdexcept>
#include <functional>
#include <vulkan/vulkan_core.h>
namespace gfg {
namespace {
constexpr auto usage=VK_IMAGE_USAGE_STORAGE_BIT|VK_IMAGE_USAGE_SAMPLED_BIT;
VkExtent2D validate(VkExtent2D e,mako::backend::FrameEncoding encoding){
 if(encoding!=mako::backend::FrameEncoding::Sdr8)
  throw std::runtime_error("GFG Open currently supports SDR8; use legacy FG for HDR");
 if(!e.width||!e.height||e.width>16384||e.height>16384)
  throw std::runtime_error("Invalid GFG Open frame extent");
 return e;
}
std::vector<vk::Image> imports(const vk::Vulkan& v,ls::FileDescriptorScope& f,VkExtent2D e){
 std::vector<vk::Image> a;a.reserve(f.size());
 for(size_t i=0,n=f.size();i<n;i++)a.emplace_back(v,e,VK_FORMAT_R8G8B8A8_UNORM,usage,f.take());
 return a;
}
vk::Barrier barrier(const vk::Image& i,VkImageLayout old=VK_IMAGE_LAYOUT_GENERAL){
 return {.sType=VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER,
 .srcAccessMask=old==VK_IMAGE_LAYOUT_UNDEFINED?0u:VK_ACCESS_SHADER_WRITE_BIT,
 .dstAccessMask=VK_ACCESS_SHADER_READ_BIT|VK_ACCESS_SHADER_WRITE_BIT,
 .oldLayout=old,.newLayout=VK_IMAGE_LAYOUT_GENERAL,
 .srcQueueFamilyIndex=VK_QUEUE_FAMILY_IGNORED,.dstQueueFamilyIndex=VK_QUEUE_FAMILY_IGNORED,
 .image=i.handle(),.subresourceRange={VK_IMAGE_ASPECT_COLOR_BIT,0,1,0,1}};
}
}
OpenContext::OpenContext(const vk::Vulkan& vk,ls::FileDescriptorScope& src,
 ls::FileDescriptorScope& dst,ls::FileDescriptorScope& sync,VkExtent2D e,mako::backend::FrameEncoding encoding)
 :v(vk),extent(validate(e,encoding)),tiles{(e.width+7)/8,(e.height+7)/8},
 sources{vk::Image(v,e,VK_FORMAT_R8G8B8A8_UNORM,usage,src.take()),
         vk::Image(v,e,VK_FORMAT_R8G8B8A8_UNORM,usage,src.take())},
 outputs(imports(v,dst,e)),
 coarseF(v,tiles,VK_FORMAT_R32G32B32A32_SFLOAT),coarseB(v,tiles,VK_FORMAT_R32G32B32A32_SFLOAT),
 flowF(v,tiles,VK_FORMAT_R32G32B32A32_SFLOAT),flowB(v,tiles,VK_FORMAT_R32G32B32A32_SFLOAT),
 shared(v,0,sync.take()),ready(v,0),fence(v),
 coarseShader(v,embedded::flow,0,6,1,0),refineShader(v,embedded::refine,0,6,1,0),
 composeShader(v,embedded::compose,0,5,1,0),
 pool(v,{.sets=static_cast<uint32_t>(4+2*outputs.size()),
 .uniform_buffers=static_cast<uint32_t>(4+2*outputs.size()),
 .samplers=0,.sampled_images=0,.storage_images=static_cast<uint32_t>(24+10*outputs.size())}),
 pairParams(v,Params{{e.width,e.height,tiles.width,tiles.height},{0,0,0,0}}){
 if(outputs.empty())throw std::runtime_error("GFG Open requires output images");
 outputParams.reserve(outputs.size());composeSets.resize(outputs.size());
 for(size_t i=0;i<outputs.size();i++)outputParams.emplace_back(v,Params{{e.width,e.height,tiles.width,tiles.height},{0,0,0,0}});
 for(size_t phase=0;phase<2;phase++){
  const auto& a=phase?sources.first:sources.second; // previous
  const auto& b=phase?sources.second:sources.first; // current
  coarseSets[phase]=std::make_unique<vk::DescriptorSet>(v,pool,coarseShader,
   std::vector<ls::R<const vk::Image>>{},std::vector<ls::R<const vk::Image>>{a,b,coarseF,coarseB,flowF,flowB},
   std::vector<ls::R<const vk::Sampler>>{},std::vector<ls::R<const vk::Buffer>>{pairParams});
  refineSets[phase]=std::make_unique<vk::DescriptorSet>(v,pool,refineShader,
   std::vector<ls::R<const vk::Image>>{},std::vector<ls::R<const vk::Image>>{a,b,coarseF,coarseB,flowF,flowB},
   std::vector<ls::R<const vk::Sampler>>{},std::vector<ls::R<const vk::Buffer>>{pairParams});
  for(size_t i=0;i<outputs.size();i++)composeSets[i][phase]=std::make_unique<vk::DescriptorSet>(v,pool,composeShader,
   std::vector<ls::R<const vk::Image>>{},std::vector<ls::R<const vk::Image>>{a,b,flowF,flowB,outputs[i]},
   std::vector<ls::R<const vk::Sampler>>{},std::vector<ls::R<const vk::Buffer>>{outputParams[i]});
 }
 // Only internal fields need a layout transition; imported transport is
 // GENERAL under the renderer's external timeline semaphore contract.
 vk::CommandBuffer init(v);init.begin(v);
 std::array transitions{barrier(coarseF,VK_IMAGE_LAYOUT_UNDEFINED),barrier(coarseB,VK_IMAGE_LAYOUT_UNDEFINED),
                       barrier(flowF,VK_IMAGE_LAYOUT_UNDEFINED),barrier(flowB,VK_IMAGE_LAYOUT_UNDEFINED)};
 v.df().CmdPipelineBarrier(init.handle(),VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT,VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,0,0,nullptr,0,nullptr,transitions.size(),transitions.data());
 init.end(v);init.submit(v);
 std::clog<<"GFG Open: backend=color-flow-v1 tile=8 search=16 selective-refinement=3 occlusion=bidirectional history=validated encoding=sdr8\n";
}
void OpenContext::prepare(){
 if(scheduled&&!fence.wait(v,250000000))throw std::runtime_error("GFG Open previous-work fence timed out");
}
void OpenContext::record(size_t count,bool history){
 prepass=std::make_unique<vk::CommandBuffer>(v);prepass->begin(v);
 std::array inputBarriers{barrier(sources.first),barrier(sources.second),barrier(flowF),barrier(flowB)};
 prepass->dispatch(v,coarseShader,*coarseSets[frame%2],inputBarriers,(tiles.width+7)/8,(tiles.height+7)/8,1);
 std::array coarseBarriers{barrier(coarseF),barrier(coarseB)};
 prepass->dispatch(v,refineShader,*refineSets[frame%2],coarseBarriers,(tiles.width+7)/8,(tiles.height+7)/8,1);
 prepass->end(v);
 commands.clear();commands.reserve(count);
 if(!history)for(size_t i=0;i<count;i++){
  commands.emplace_back(v);auto& c=commands.back();c.begin(v);
  std::array flowBarriers{barrier(flowF),barrier(flowB),barrier(outputs[i])};
  c.dispatch(v,composeShader,*composeSets[i][frame%2],flowBarriers,(extent.width+7)/8,(extent.height+7)/8,1);c.end(v);
 }
}
void OpenContext::submitPrepass(VkFence completion){
 fence.reset(v);scheduled=true;
 prepass->submit(v,{},shared.handle(),idx,{},ready.handle(),idx,completion);
 ++idx;
}
void OpenContext::scheduleFrames(){scheduleFrames({});}
void OpenContext::scheduleFrames(std::span<const float> timestamps){
 size_t count=timestamps.empty()?outputs.size():timestamps.size();
 if(count>outputs.size())throw std::runtime_error("Too many GFG Open timestamps");
 float previous=0;
 for(float t:timestamps){if(!std::isfinite(t)||t<=previous||t>=1)throw std::runtime_error("Invalid GFG Open interpolation timestamp");previous=t;}
 prepare();
 Params params{{extent.width,extent.height,tiles.width,tiles.height},{0,frame>1?1.f:0.f,frame>0?1.f:0.f,0}};
 pairParams.write(v,params);
 for(size_t i=0;i<count;i++){
  params.timing={timestamps.empty()?float(i+1)/float(count+1):timestamps[i],frame>0?1.f:0.f,0,0};
  outputParams[i].write(v,params);
 }
 record(count,false);submitPrepass(VK_NULL_HANDLE);
 for(size_t i=0;i<count;i++)commands[i].submit(v,{},ready.handle(),idx-1,{},shared.handle(),idx+i,i+1==count?fence.handle():VK_NULL_HANDLE);
 idx+=count;++frame;
}
void OpenContext::scheduleFrameHistory(){
 prepare();
 pairParams.write(v,Params{{extent.width,extent.height,tiles.width,tiles.height},{0,frame>1?1.f:0.f,0,0}});
 record(0,true);submitPrepass(fence.handle());++frame;
}
bool OpenContext::waitForIdle(uint64_t ns)const{return !scheduled||fence.wait(v,ns);}
}
