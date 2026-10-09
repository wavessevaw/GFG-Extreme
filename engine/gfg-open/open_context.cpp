// SPDX-License-Identifier: GPL-3.0-or-later
#include "open_context.hpp"
#include "embedded.hpp"
#include <cmath>
#include <iostream>
#include <stdexcept>
#include <functional>
#include <fstream>
#include <iomanip>
#include <filesystem>
#include <chrono>
#include <unistd.h>
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
 :v(vk),extent(validate(e,encoding)),tiles{(e.width+15)/16,(e.height+15)/16},
 sources{vk::Image(v,e,VK_FORMAT_R8G8B8A8_UNORM,usage,src.take()),
         vk::Image(v,e,VK_FORMAT_R8G8B8A8_UNORM,usage,src.take())},
 outputs(imports(v,dst,e)),
 coarseF(v,tiles,VK_FORMAT_R32G32B32A32_SFLOAT),coarseB(v,tiles,VK_FORMAT_R32G32B32A32_SFLOAT),
 flowF(v,tiles,VK_FORMAT_R32G32B32A32_SFLOAT),flowB(v,tiles,VK_FORMAT_R32G32B32A32_SFLOAT),
 pyrPrevious(v,{(e.width+3)/4,(e.height+3)/4},VK_FORMAT_R32G32B32A32_SFLOAT),
 pyrCurrent(v,{(e.width+3)/4,(e.height+3)/4},VK_FORMAT_R32G32B32A32_SFLOAT),
 shared(v,0,sync.take()),ready(v,0),fence(v),
 pyramidShader(v,embedded::pyramid,0,4,1,0),
 coarseShader(v,embedded::flow,0,8,1,0),refineShader(v,embedded::refine,0,6,1,0),
 composeShader(v,embedded::compose,0,5,1,0),
 pool(v,{.sets=static_cast<uint32_t>(6+2*outputs.size()),
 .uniform_buffers=static_cast<uint32_t>(6+2*outputs.size()),
 .samplers=0,.sampled_images=0,.storage_images=static_cast<uint32_t>(36+10*outputs.size())}),
 pairParams(v,Params{{e.width,e.height,tiles.width,tiles.height},{0,0,0,0}}){
 if(outputs.empty())throw std::runtime_error("GFG Open requires output images");
 outputParams.reserve(outputs.size());composeSets.resize(outputs.size());commands.resize(outputs.size());lastOutputParams.resize(outputs.size());
 for(size_t i=0;i<outputs.size();i++)outputParams.emplace_back(v,Params{{e.width,e.height,tiles.width,tiles.height},{0,0,0,0}});
 for(size_t phase=0;phase<2;phase++){
  const auto& a=phase?sources.first:sources.second; // previous
  const auto& b=phase?sources.second:sources.first; // current
  pyramidSets[phase]=std::make_unique<vk::DescriptorSet>(v,pool,pyramidShader,
   std::vector<ls::R<const vk::Image>>{},std::vector<ls::R<const vk::Image>>{a,b,pyrPrevious,pyrCurrent},
   std::vector<ls::R<const vk::Sampler>>{},std::vector<ls::R<const vk::Buffer>>{pairParams});
  coarseSets[phase]=std::make_unique<vk::DescriptorSet>(v,pool,coarseShader,
   std::vector<ls::R<const vk::Image>>{},std::vector<ls::R<const vk::Image>>{a,b,coarseF,coarseB,flowF,flowB,pyrPrevious,pyrCurrent},
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
                       barrier(flowF,VK_IMAGE_LAYOUT_UNDEFINED),barrier(flowB,VK_IMAGE_LAYOUT_UNDEFINED),
                       barrier(pyrPrevious,VK_IMAGE_LAYOUT_UNDEFINED),barrier(pyrCurrent,VK_IMAGE_LAYOUT_UNDEFINED)};
 v.df().CmdPipelineBarrier(init.handle(),VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT,VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,0,0,nullptr,0,nullptr,transitions.size(),transitions.data());
 init.end(v);init.submit(v);
 initTiming();
 std::clog<<"GFG Open: backend=color-flow-v2 reference_patch_cache=on budget=source-quarter-capped-8ms tile=16 search=16 selective-refinement=3 occlusion=bidirectional history=validated encoding=sdr8\n";
}
void OpenContext::initTiming(){
 auto get=v.fi().GetDeviceProcAddr;
 auto create=reinterpret_cast<PFN_vkCreateQueryPool>(get(v.dev(),"vkCreateQueryPool"));
 destroyQueries=reinterpret_cast<PFN_vkDestroyQueryPool>(get(v.dev(),"vkDestroyQueryPool"));
 readQueries=reinterpret_cast<PFN_vkGetQueryPoolResults>(get(v.dev(),"vkGetQueryPoolResults"));
 resetQueries=reinterpret_cast<PFN_vkCmdResetQueryPool>(get(v.dev(),"vkCmdResetQueryPool"));
 writeTimestamp=reinterpret_cast<PFN_vkCmdWriteTimestamp>(get(v.dev(),"vkCmdWriteTimestamp"));
 VkPhysicalDeviceProperties props{};v.fi().GetPhysicalDeviceProperties(v.physdev(),&props);
 uint32_t n=0;v.fi().GetPhysicalDeviceQueueFamilyProperties(v.physdev(),&n,nullptr);
 std::vector<VkQueueFamilyProperties> families(n);
 v.fi().GetPhysicalDeviceQueueFamilyProperties(v.physdev(),&n,families.data());
 if(v.queueFamilyIndex()<n)timestampBits=families[v.queueFamilyIndex()].timestampValidBits;
 timestampPeriod=props.limits.timestampPeriod;
 if(create&&destroyQueries&&readQueries&&resetQueries&&writeTimestamp&&timestampBits&&timestampPeriod>0){
  VkQueryPoolCreateInfo info{VK_STRUCTURE_TYPE_QUERY_POOL_CREATE_INFO};
  info.queryType=VK_QUERY_TYPE_TIMESTAMP;info.queryCount=uint32_t(2+2*outputs.size());
  if(create(v.dev(),&info,nullptr,&queries)!=VK_SUCCESS)queries=VK_NULL_HANDLE;
 }
 if(!queries){
  budget.disableWithoutTiming();
  publishTiming(0,0);
  std::clog<<"GFG Open: performance-fallback=real-frame reason=gpu-timing-unavailable; select legacy FG and restart for interpolation\n";
 }
}
void OpenContext::publishTiming(double prepassMs,double compositionMs) const{
 const char* dir=std::getenv("GFG_OPEN_DIAGNOSTICS_DIR");
 if(!dir||!*dir)return;
 try{
  std::filesystem::path base(dir);std::filesystem::create_directories(base);
  const auto name=std::to_string(getpid())+".json";
  const auto path=base/name,tmp=base/(name+".tmp");
  std::ofstream out(tmp);
  const auto now=std::chrono::duration<double>(std::chrono::system_clock::now().time_since_epoch()).count();
  out<<std::setprecision(17)<<"{\"backend\":\"color-flow-v2\",\"pid\":"<<getpid()
     <<",\"timing_available\":"<<(queries?"true":"false")
     <<",\"prepass_ms\":"<<prepassMs<<",\"composition_ms\":"<<compositionMs
     <<",\"gpu_compute_ms\":"<<prepassMs+compositionMs<<",\"budget_ms\":"<<budget.currentLimitMs
     <<",\"passthrough\":"<<(budget.passthrough()?"true":"false")<<",\"safety_latched\":"<<(budget.bypass?"true":"false")
     <<",\"recovery_probe\":"<<(budget.probing?"true":"false")<<",\"probe_attempts\":"<<budget.probeAttempts
     <<",\"recoveries\":"<<budget.recoveries<<",\"next_probe_frames\":"<<budget.cooldownFrames
     <<",\"interpolation_attempted\":"<<(!budget.passthrough()?"true":"false")
     <<",\"last_active_gpu_ms\":"<<lastActiveGpuMs
     <<",\"last_active_prepass_ms\":"<<lastActivePrepassMs
     <<",\"last_active_composition_ms\":"<<lastActiveCompositionMs
     <<",\"last_probe_gpu_ms\":"<<lastProbeGpuMs
     <<",\"last_failed_probe_gpu_ms\":"<<lastFailedProbeGpuMs
     <<",\"budget_policy\":\"source-period-quarter-capped-8ms\""
     <<",\"recovery_budget_ms\":"<<budget.recoveryThresholdMs()
     <<",\"interpolation_scheduled_outputs\":"<<interpolatedOutputs
     <<",\"real_copy_scheduled_outputs\":"<<copiedOutputs
     <<",\"samples\":"<<budget.samples
     <<",\"source_resolution\":["<<extent.width<<","<<extent.height<<"]"
     <<",\"motion_tiles\":["<<tiles.width<<","<<tiles.height<<"],\"updated_unix_s\":"<<now<<"}\n";
  out.close();if(out)std::filesystem::rename(tmp,path);
 }catch(...){ /* Diagnostics must never disrupt rendering. */ }
}
OpenContext::~OpenContext(){
 if(queries&&destroyQueries)destroyQueries(v.dev(),queries,nullptr);
}
void OpenContext::collectTiming(){
 if(!queries||!scheduledCount)return;
 std::vector<uint64_t> times(2+2*scheduledCount);
 if(readQueries(v.dev(),queries,0,uint32_t(times.size()),times.size()*sizeof(uint64_t),times.data(),sizeof(uint64_t),VK_QUERY_RESULT_64_BIT)!=VK_SUCCESS)return;
 const uint64_t mask=timestampBits>=64?~uint64_t(0):(uint64_t(1)<<timestampBits)-1;
 double ticks=double((times[1]-times[0])&mask);
 for(size_t i=2;i<times.size();i+=2)ticks+=double((times[i+1]-times[i])&mask);
 const double prepassMs=double((times[1]-times[0])&mask)*double(timestampPeriod)/1e6;
 const double ms=ticks*double(timestampPeriod)/1e6;
 const bool was=budget.bypass,wasProbe=budget.probing;
 if(!budget.passthrough()){
  lastActiveGpuMs=ms;lastActivePrepassMs=prepassMs;lastActiveCompositionMs=ms-prepassMs;
  if(wasProbe)lastProbeGpuMs=ms;
 }
 budget.observe(ms);
 if(wasProbe&&!budget.probing&&budget.bypass)lastFailedProbeGpuMs=ms;
 if((!was&&budget.bypass)||(wasProbe&&!budget.probing)||budget.samples%120==1)publishTiming(prepassMs,ms-prepassMs);
 if(!was&&budget.bypass)std::clog<<"GFG Open: performance-fallback=real-frame reason=gpu-budget gpu_ms="<<ms<<" limit_ms="<<budget.currentLimitMs<<"; select legacy FG and restart for interpolation\n";
 else if(wasProbe&&!budget.probing)std::clog<<"GFG Open: recovery="<<(budget.bypass?"retry-later":"interpolation-restored")<<" gpu_ms="<<ms<<" next_probe_frames="<<budget.cooldownFrames<<"\n";
 else if(budget.samples%120==1)std::clog<<"GFG Open: gpu_ms="<<ms<<" limit_ms="<<GpuBudget::limitMs<<" passthrough="<<budget.passthrough()<<" recovery_probe="<<budget.probing<<" next_probe_frames="<<budget.cooldownFrames<<"\n";
}
void OpenContext::prepare(){
 if(scheduled&&!fence.wait(v,250000000))throw std::runtime_error("GFG Open previous-work fence timed out");
 if(scheduled)collectTiming();
}
void OpenContext::writePair(const Params& p){
 if(!lastPairParams||*lastPairParams!=p){pairParams.write(v,p);lastPairParams=p;}
}
void OpenContext::writeOutput(size_t i,const Params& p){
 if(!lastOutputParams[i]||*lastOutputParams[i]!=p){outputParams[i].write(v,p);lastOutputParams[i]=p;}
}
void OpenContext::record(size_t count,bool history){
 const auto phase=frame%2;
 if(!prepasses[phase]){
  vk::CommandBuffer c(v);c.begin(v,0);
  if(queries){resetQueries(c.handle(),queries,0,uint32_t(2+2*outputs.size()));writeTimestamp(c.handle(),VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT,queries,0);}
  std::array inputBarriers{barrier(sources.first),barrier(sources.second),barrier(flowF),barrier(flowB)};
  c.dispatch(v,pyramidShader,*pyramidSets[phase],inputBarriers,((extent.width+3)/4+7)/8,((extent.height+3)/4+7)/8,1);
  std::array pyramidBarriers{barrier(pyrPrevious),barrier(pyrCurrent),barrier(flowF),barrier(flowB)};
  c.dispatch(v,coarseShader,*coarseSets[phase],pyramidBarriers,(tiles.width+7)/8,(tiles.height+7)/8,1);
  std::array coarseBarriers{barrier(coarseF),barrier(coarseB)};
  c.dispatch(v,refineShader,*refineSets[phase],coarseBarriers,(tiles.width+7)/8,(tiles.height+7)/8,1);
  if(queries)writeTimestamp(c.handle(),VK_PIPELINE_STAGE_BOTTOM_OF_PIPE_BIT,queries,1);
  c.end(v);prepasses[phase].emplace(std::move(c));
 }
 if(!history)for(size_t i=0;i<count;i++){
  if(commands[i][phase])continue;
  vk::CommandBuffer c(v);c.begin(v,0);
  if(queries)writeTimestamp(c.handle(),VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT,queries,uint32_t(2+2*i));
  std::array flowBarriers{barrier(flowF),barrier(flowB),barrier(outputs[i])};
  c.dispatch(v,composeShader,*composeSets[i][phase],flowBarriers,(extent.width+7)/8,(extent.height+7)/8,1);
  if(queries)writeTimestamp(c.handle(),VK_PIPELINE_STAGE_BOTTOM_OF_PIPE_BIT,queries,uint32_t(3+2*i));
  c.end(v);commands[i][phase].emplace(std::move(c));
 }
}
void OpenContext::submitPrepass(VkFence completion){
 fence.reset(v);scheduled=true;
 prepasses[frame%2]->submit(v,{},shared.handle(),idx,{},ready.handle(),idx,completion);
 ++idx;
}
void OpenContext::scheduleFrames(){scheduleFrames({});}
void OpenContext::scheduleFrames(std::span<const float> timestamps){
 size_t count=timestamps.empty()?outputs.size():timestamps.size();
 if(count>outputs.size())throw std::runtime_error("Too many GFG Open timestamps");
 float previous=0;
 for(float t:timestamps){if(!std::isfinite(t)||t<=previous||t>=1)throw std::runtime_error("Invalid GFG Open interpolation timestamp");previous=t;}
 const auto sourceNow=std::chrono::steady_clock::now();
 if(lastSourceTime)budget.sourceInterval(std::chrono::duration<double,std::milli>(sourceNow-*lastSourceTime).count());
 lastSourceTime=sourceNow;
 prepare();
 budget.beforeFrame(); // Periodic real-work probe; bypass frames alone cannot prove recovery.
 Params params{{extent.width,extent.height,tiles.width,tiles.height},{0,frame>1?1.f:0.f,frame>0?1.f:0.f,budget.passthrough()?1.f:0.f}};
 writePair(params);
 for(size_t i=0;i<count;i++){
  params.timing={timestamps.empty()?float(i+1)/float(count+1):timestamps[i],frame>0?1.f:0.f,0,budget.passthrough()?1.f:0.f};
  writeOutput(i,params);
 }
 if(budget.passthrough()||frame==0)copiedOutputs+=count;
 else interpolatedOutputs+=count;
 scheduledCount=count;
 record(count,false);submitPrepass(VK_NULL_HANDLE);
 for(size_t i=0;i<count;i++)commands[i][frame%2]->submit(v,{},ready.handle(),idx-1,{},shared.handle(),idx+i,i+1==count?fence.handle():VK_NULL_HANDLE);
 idx+=count;++frame;
}
void OpenContext::scheduleFrameHistory(){
 prepare();
 writePair(Params{{extent.width,extent.height,tiles.width,tiles.height},{0,frame>1?1.f:0.f,frame>0?1.f:0.f,budget.passthrough()?1.f:0.f}});
 scheduledCount=0;
 record(0,true);submitPrepass(fence.handle());++frame;
}
bool OpenContext::waitForIdle(uint64_t ns)const{return !scheduled||fence.wait(v,ns);}
}
