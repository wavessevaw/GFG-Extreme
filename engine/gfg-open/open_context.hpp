// SPDX-License-Identifier: GPL-3.0-or-later
#pragma once
#include "mako-backend/mako.hpp"
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
namespace gfg {
struct alignas(16) Params {
 std::array<uint32_t,4> size;
 std::array<float,4> timing;
};
class OpenContext {
 const vk::Vulkan& v;
 VkExtent2D extent,tiles;
 std::pair<vk::Image,vk::Image> sources;
 std::vector<vk::Image> outputs;
 vk::Image coarseF,coarseB,flowF,flowB;
 vk::TimelineSemaphore shared,ready;
 vk::Fence fence;
 vk::Shader coarseShader,refineShader,composeShader;
 vk::DescriptorPool pool;
 vk::Buffer pairParams;
 std::vector<vk::Buffer> outputParams;
 std::array<std::unique_ptr<vk::DescriptorSet>,2> coarseSets,refineSets;
 std::vector<std::array<std::unique_ptr<vk::DescriptorSet>,2>> composeSets;
 std::unique_ptr<vk::CommandBuffer> prepass;
 std::vector<vk::CommandBuffer> commands;
 uint64_t idx=1,frame=0;
 bool scheduled=false;
 void prepare();
 void record(size_t count,bool history);
 void submitPrepass(VkFence completion);
 public:
 OpenContext(const vk::Vulkan&,ls::FileDescriptorScope&,ls::FileDescriptorScope&,ls::FileDescriptorScope&,VkExtent2D,mako::backend::FrameEncoding);
 void scheduleFrames();
 void scheduleFrames(std::span<const float>);
 void scheduleFrameHistory();
 bool waitForIdle(uint64_t) const;
};
}
