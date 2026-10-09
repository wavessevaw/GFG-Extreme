// SPDX-License-Identifier: GPL-3.0-or-later
#pragma once
#include "mako-backend/mako.hpp"
#include "budget.hpp"
#include "mako-common/helpers/file_descriptors.hpp"
#include "mako-common/vulkan/buffer.hpp"
#include "mako-common/vulkan/command_buffer.hpp"
#include "mako-common/vulkan/descriptor_pool.hpp"
#include "mako-common/vulkan/descriptor_set.hpp"
#include "mako-common/vulkan/fence.hpp"
#include "mako-common/vulkan/image.hpp"
#include "mako-common/vulkan/shader.hpp"
#include "mako-common/vulkan/timeline_semaphore.hpp"
#include <memory>
#include <array>
#include <vector>
#include <span>
#include <optional>
#include <chrono>
namespace gfg {
struct alignas(16) Params {
 std::array<uint32_t,4> size;
 std::array<float,4> timing;
 bool operator==(const Params&) const = default;
};
class OpenContext {
 const vk::Vulkan& v;
 VkExtent2D extent,tiles;
 std::pair<vk::Image,vk::Image> sources;
 std::vector<vk::Image> outputs;
 vk::Image coarseF,coarseB,flowF,flowB,pyrPrevious,pyrCurrent;
 vk::TimelineSemaphore shared,ready;
 vk::Fence fence;
 vk::Shader pyramidShader,coarseShader,refineShader,composeShader;
 vk::DescriptorPool pool;
 vk::Buffer pairParams;
 std::vector<vk::Buffer> outputParams;
 std::array<std::unique_ptr<vk::DescriptorSet>,2> pyramidSets,coarseSets,refineSets;
 std::vector<std::array<std::unique_ptr<vk::DescriptorSet>,2>> composeSets;
 std::array<std::optional<vk::CommandBuffer>,2> prepasses;
 std::vector<std::array<std::optional<vk::CommandBuffer>,2>> commands;
 std::optional<Params> lastPairParams;
 std::vector<std::optional<Params>> lastOutputParams;
 void writePair(const Params&);
 void writeOutput(size_t,const Params&);
 uint64_t idx=1,frame=0;
 bool scheduled=false;
 GpuBudget budget;
 std::optional<std::chrono::steady_clock::time_point> lastSourceTime;
 // Retain full-compute costs while cheaper bypass frames continue.
 double lastActiveGpuMs=0, lastActivePrepassMs=0, lastActiveCompositionMs=0;
 double lastProbeGpuMs=0, lastFailedProbeGpuMs=0;
 VkQueryPool queries=VK_NULL_HANDLE;
 PFN_vkDestroyQueryPool destroyQueries=nullptr;
 PFN_vkGetQueryPoolResults readQueries=nullptr;
 PFN_vkCmdResetQueryPool resetQueries=nullptr;
 PFN_vkCmdWriteTimestamp writeTimestamp=nullptr;
 float timestampPeriod=0;
 uint32_t timestampBits=0;
 size_t scheduledCount=0;
 void initTiming();
 void collectTiming();
 void publishTiming(double prepassMs,double compositionMs) const;
 void prepare();
 void record(size_t count,bool history);
 void submitPrepass(VkFence completion);
 public:
 OpenContext(const vk::Vulkan&,ls::FileDescriptorScope&,ls::FileDescriptorScope&,ls::FileDescriptorScope&,VkExtent2D,mako::backend::FrameEncoding);
 ~OpenContext();
 void scheduleFrames();
 void scheduleFrames(std::span<const float>);
 void scheduleFrameHistory();
 bool waitForIdle(uint64_t) const;
};
}
