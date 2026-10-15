// SPDX-License-Identifier: GPL-3.0-or-later
// Host-call simulation only: no GPU, proprietary shader or Vulkan loader.
#pragma once
#include <vulkan/vulkan_core.h>
#include <cstdint>
#include <functional>
#include <iostream>
#include <memory>
#include <optional>
#include <string>
#include <vector>

namespace ls {
template<class T> using R = std::reference_wrapper<T>;
template<class T> using lazy = std::optional<T>;
}
namespace mako {}
namespace sim {
inline std::string owner = "external";
inline std::string phase = "setup";
inline size_t nextImage = 0;
inline size_t nextDispatch = 0;
inline unsigned pass = 0;
inline unsigned frame = 0;
inline bool emit = true;
inline unsigned bytesPerPixel(VkFormat format) {
    switch (format) {
        case VK_FORMAT_R8_UNORM: return 1;
        case VK_FORMAT_R8G8B8A8_UNORM: return 4;
        case VK_FORMAT_R16G16B16A16_SFLOAT: return 8;
        default: throw std::runtime_error("unmodeled image format");
    }
}
template<class T> void ids(const std::vector<T>& values) {
    std::cout << '[';
    for (size_t i=0; i<values.size(); ++i) {
        if (i) std::cout << ',';
        std::cout << values[i];
    }
    std::cout << ']';
}
}
namespace vk {
struct Vulkan {};
struct ImageMemoryPool {};
struct DescriptorPool {};
struct Buffer {};
struct Sampler {};
struct Shader { std::string name; };
using Barrier = VkImageMemoryBarrier;
struct Image {
    size_t id;
    VkExtent2D extent;
    VkImage image;
    Image(const Vulkan&, VkExtent2D size, std::shared_ptr<ImageMemoryPool>,
          VkFormat format=VK_FORMAT_R8G8B8A8_UNORM,
          VkImageUsageFlags=VK_IMAGE_USAGE_STORAGE_BIT|VK_IMAGE_USAGE_SAMPLED_BIT)
        : id(++sim::nextImage), extent(size), image(reinterpret_cast<VkImage>(id)) {
        if (sim::emit) std::cout << "{\"event\":\"image\",\"id\":" << id
            << ",\"owner\":\"" << sim::owner << "\",\"width\":" << size.width
            << ",\"height\":" << size.height << ",\"format\":" << format
            << ",\"logical_bytes\":" << uint64_t(size.width)*size.height*sim::bytesPerPixel(format)
            << "}\n";
    }
    VkExtent2D getExtent() const { return extent; }
    const VkImage& handle() const { return image; }
};
struct DescriptorSet {
    std::vector<size_t> reads, writes;
    DescriptorSet(const Vulkan&, const DescriptorPool&, const Shader&,
        const std::vector<ls::R<const Image>>& inputs,
        const std::vector<ls::R<const Image>>& outputs,
        const std::vector<ls::R<const Sampler>>&,
        const std::vector<ls::R<const Buffer>>&) {
        for (const auto& value:inputs) reads.push_back(value.get().id);
        for (const auto& value:outputs) writes.push_back(value.get().id);
    }
};
struct CommandBuffer {
    void dispatch(const Vulkan&, const Shader& shader, const DescriptorSet& set,
        const std::vector<Barrier>& barriers, unsigned x,unsigned y,unsigned z) const {
        if (!sim::emit) return;
        std::cout << "{\"event\":\"dispatch\",\"id\":" << ++sim::nextDispatch
            << ",\"frame\":" << sim::frame << ",\"phase\":\"" << sim::phase << "\",\"output\":" << sim::pass
            << ",\"shader\":\"" << shader.name << "\",\"groups\":[" << x << ',' << y << ',' << z
            << "],\"image_barriers\":" << barriers.size() << ",\"reads\":";
        sim::ids(set.reads); std::cout << ",\"writes\":"; sim::ids(set.writes);
        std::cout << "}\n";
    }
};
}
