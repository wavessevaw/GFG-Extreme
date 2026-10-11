/* SPDX-License-Identifier: GPL-3.0-or-later */
// Uses the pinned MAKO production scaler on a real Vulkan device (Lavapipe
// in CI). No mock pixel math and no licensed LSFG payload required.
#include "spatial_scaler.hpp"
#include "image_transfer.hpp"
#include "mako-common/vulkan/buffer.hpp"
#include "mako-common/vulkan/command_buffer.hpp"
#include "mako-common/vulkan/image.hpp"
#include "mako-common/vulkan/vulkan.hpp"
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <iostream>
#include <optional>
#include <stdexcept>
#include <string>
#include <type_traits>
#include <vector>

using mako::layer::SpatialScaler;
using mako::cli::images::imageBarrier;
using mako::cli::images::uploadImage;
static PFN_vkCmdBlitImage originalBlit{};
static uint64_t blits{};
static void VKAPI_CALL countedBlit(VkCommandBuffer command, VkImage source,
        VkImageLayout sourceLayout, VkImage destination, VkImageLayout destinationLayout,
        uint32_t count, const VkImageBlit* regions, VkFilter filter) {
    ++blits;
    originalBlit(command, source, sourceLayout, destination, destinationLayout,
        count, regions, filter);
}
static void require(bool good, const char* reason) {
    if (!good) throw std::runtime_error(reason);
}
template<class Function> static void rejected(Function f) {
    bool failed=false;
    try { f(); } catch (const std::exception&) { failed=true; }
    require(failed, "invalid input accepted");
}
static std::vector<uint8_t> pattern(VkExtent2D size, unsigned phase) {
    std::vector<uint8_t> pixels(size.width*size.height*4);
    for (uint32_t y=0; y<size.height; ++y) for (uint32_t x=0; x<size.width; ++x) {
        const auto p=(y*size.width+x)*4;
        pixels[p]=static_cast<uint8_t>((x*17+y*3+phase*43)%256);
        pixels[p+1]=static_cast<uint8_t>((y*31+x*7+phase*19)%256);
        pixels[p+2]=((x+phase*3)/5+y/7)%2 ? 255 : 0;
        pixels[p+3]=static_cast<uint8_t>((x+y+phase)%256);
    }
    return pixels;
}
static std::vector<uint8_t> download(const vk::Vulkan& vk, const vk::Image& image) {
    const std::vector<uint8_t> zeroes(image.getExtent().width*image.getExtent().height*4);
    const vk::Buffer staging(vk,zeroes.data(),zeroes.size(),VK_BUFFER_USAGE_TRANSFER_DST_BIT);
    const vk::CommandBuffer command(vk);
    command.begin(vk);
    const auto barrier=imageBarrier(image.handle(),VK_ACCESS_MEMORY_WRITE_BIT,
        VK_ACCESS_TRANSFER_READ_BIT,VK_IMAGE_LAYOUT_GENERAL,VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL);
    vk.df().CmdPipelineBarrier(command.handle(),VK_PIPELINE_STAGE_ALL_COMMANDS_BIT,
        VK_PIPELINE_STAGE_TRANSFER_BIT,0,0,nullptr,0,nullptr,1,&barrier);
    const VkBufferImageCopy region{.imageSubresource={VK_IMAGE_ASPECT_COLOR_BIT,0,0,1},
        .imageExtent={image.getExtent().width,image.getExtent().height,1}};
    vk.df().CmdCopyImageToBuffer(command.handle(),image.handle(),
        VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL,staging.handle(),1,&region);
    // Make transfer results available to the host, even on non-coherent heaps.
    const VkBufferMemoryBarrier host{.sType=VK_STRUCTURE_TYPE_BUFFER_MEMORY_BARRIER,
        .srcAccessMask=VK_ACCESS_TRANSFER_WRITE_BIT,.dstAccessMask=VK_ACCESS_HOST_READ_BIT,
        .srcQueueFamilyIndex=VK_QUEUE_FAMILY_IGNORED,.dstQueueFamilyIndex=VK_QUEUE_FAMILY_IGNORED,
        .buffer=staging.handle(),.offset=0,.size=VK_WHOLE_SIZE};
    vk.df().CmdPipelineBarrier(command.handle(),VK_PIPELINE_STAGE_TRANSFER_BIT,
        VK_PIPELINE_STAGE_HOST_BIT,0,0,nullptr,1,&host,0,nullptr);
    command.end(vk);command.submit(vk);
    return staging.read(vk);
}
static void record(const vk::Vulkan& vk, SpatialScaler& scaler, const vk::Image& input,
        const vk::Image& output, VkImageLayout inputLayout=VK_IMAGE_LAYOUT_GENERAL) {
    const vk::CommandBuffer command(vk);command.begin(vk);
    scaler.recordSourceToPresentation(vk,command,input.handle(),output.handle(),
        inputLayout,VK_IMAGE_LAYOUT_UNDEFINED,VK_IMAGE_LAYOUT_GENERAL);
    command.end(vk);command.submit(vk);
}

// TimestampQueryPool is inserted here by the source preparation helper.
// Timestamp utility adapted from MAKO CLI quality.cpp (GPL-3.0-or-later).
    template<typename Function>
    [[nodiscard]] Function deviceFunction(
            const vk::Vulkan& vk, const char* name) {
        const auto function = reinterpret_cast<Function>(
            vk.fi().GetDeviceProcAddr(vk.dev(), name)
        );
        if (!function)
            throw ls::vulkan_error(
                "failed to get device proc addr for " + std::string(name)
            );
        return function;
    }

    class TimestampQueryPool {
    public:
        TimestampQueryPool(const vk::Vulkan& vk, const uint32_t queryCount) :
            device(vk.dev()),
            create(deviceFunction<PFN_vkCreateQueryPool>(vk, "vkCreateQueryPool")),
            destroy(deviceFunction<PFN_vkDestroyQueryPool>(vk, "vkDestroyQueryPool")),
            resetFunction(deviceFunction<PFN_vkCmdResetQueryPool>(
                vk, "vkCmdResetQueryPool"
            )),
            writeFunction(deviceFunction<PFN_vkCmdWriteTimestamp>(
                vk, "vkCmdWriteTimestamp"
            )),
            resultsFunction(deviceFunction<PFN_vkGetQueryPoolResults>(
                vk, "vkGetQueryPoolResults"
            )),
            count(queryCount) {
            uint32_t familyCount{};
            vk.fi().GetPhysicalDeviceQueueFamilyProperties(
                vk.physdev(), &familyCount, nullptr
            );
            std::vector<VkQueueFamilyProperties> families(familyCount);
            vk.fi().GetPhysicalDeviceQueueFamilyProperties(
                vk.physdev(), &familyCount, families.data()
            );
            if (vk.queueFamilyIndex() >= families.size())
                throw ls::vulkan_error("timestamp queue family is out of range");
            this->validBits = families.at(
                vk.queueFamilyIndex()
            ).timestampValidBits;
            if (this->validBits == 0)
                throw ls::vulkan_error(
                    "selected Vulkan queue does not support timestamps"
                );
            if (this->validBits > 64)
                throw ls::vulkan_error(
                    "selected Vulkan queue reports an invalid timestamp width"
                );

            VkPhysicalDeviceProperties properties{};
            vk.fi().GetPhysicalDeviceProperties(vk.physdev(), &properties);
            this->periodNanoseconds = properties.limits.timestampPeriod;
            if (!std::isfinite(this->periodNanoseconds) ||
                    this->periodNanoseconds <= 0.0F) {
                throw ls::vulkan_error(
                    "selected Vulkan device reports an invalid timestamp period"
                );
            }

            const VkQueryPoolCreateInfo info{
                .sType = VK_STRUCTURE_TYPE_QUERY_POOL_CREATE_INFO,
                .queryType = VK_QUERY_TYPE_TIMESTAMP,
                .queryCount = queryCount,
            };
            const auto result = this->create(
                this->device, &info, nullptr, &this->pool
            );
            if (result != VK_SUCCESS)
                throw ls::vulkan_error(result, "vkCreateQueryPool() failed");
        }

        ~TimestampQueryPool() {
            if (this->pool != VK_NULL_HANDLE)
                this->destroy(this->device, this->pool, nullptr);
        }

        TimestampQueryPool(const TimestampQueryPool&) = delete;
        TimestampQueryPool& operator=(const TimestampQueryPool&) = delete;

        void reset(const VkCommandBuffer commandBuffer) const {
            this->resetFunction(commandBuffer, this->pool, 0, this->count);
        }

        void write(const VkCommandBuffer commandBuffer,
                const VkPipelineStageFlagBits stage,
                const uint32_t query) const {
            this->writeFunction(commandBuffer, stage, this->pool, query);
        }

        [[nodiscard]] std::vector<double> microseconds() const {
            std::vector<uint64_t> timestamps(this->count);
            const auto result = this->resultsFunction(
                this->device, this->pool, 0, this->count,
                timestamps.size() * sizeof(uint64_t), timestamps.data(),
                sizeof(uint64_t), VK_QUERY_RESULT_64_BIT
            );
            if (result != VK_SUCCESS)
                throw ls::vulkan_error(
                    result, "vkGetQueryPoolResults() failed"
                );

            const uint64_t mask = this->validBits == 64
                ? UINT64_MAX : (uint64_t{1} << this->validBits) - 1;
            std::vector<double> samples;
            samples.reserve(this->count / 2);
            for (uint32_t query = 0; query < this->count; query += 2) {
                const uint64_t elapsed =
                    (timestamps.at(query + 1) - timestamps.at(query)) & mask;
                samples.push_back(
                    static_cast<double>(elapsed) *
                    static_cast<double>(this->periodNanoseconds) / 1000.0
                );
            }
            return samples;
        }

        [[nodiscard]] uint32_t timestampValidBits() const {
            return this->validBits;
        }

        [[nodiscard]] float timestampPeriodNanoseconds() const {
            return this->periodNanoseconds;
        }

    private:
        VkDevice device{VK_NULL_HANDLE};
        PFN_vkCreateQueryPool create{};
        PFN_vkDestroyQueryPool destroy{};
        PFN_vkCmdResetQueryPool resetFunction{};
        PFN_vkCmdWriteTimestamp writeFunction{};
        PFN_vkGetQueryPoolResults resultsFunction{};
        VkQueryPool pool{VK_NULL_HANDLE};
        uint32_t count{};
        uint32_t validBits{};
        float periodNanoseconds{};
    };



static void integration(vk::Vulkan& vk) {
    unsigned comparisons=0;
    for (const auto outputSize : {VkExtent2D{320,200},VkExtent2D{317,193}})
    for (const float factor : {1.25F,1.5F,2.0F})
    for (const float sharpness : {0.0F,0.5F,1.0F}) {
        const VkExtent2D inputSize{static_cast<uint32_t>(outputSize.width/factor),
            static_cast<uint32_t>(outputSize.height/factor)};
        std::vector<vk::Image> inputs;
        for(unsigned i=0;i<3;++i) inputs.emplace_back(vk,inputSize,VK_FORMAT_R8G8B8A8_UNORM,
            VK_IMAGE_USAGE_TRANSFER_SRC_BIT|VK_IMAGE_USAGE_TRANSFER_DST_BIT|VK_IMAGE_USAGE_SAMPLED_BIT);
        const vk::Image baselineOutput(vk,outputSize,VK_FORMAT_R8G8B8A8_UNORM,
            VK_IMAGE_USAGE_TRANSFER_SRC_BIT|VK_IMAGE_USAGE_TRANSFER_DST_BIT|VK_IMAGE_USAGE_SAMPLED_BIT);
        const vk::Image fusionOutput(vk,outputSize,VK_FORMAT_R8G8B8A8_UNORM,
            VK_IMAGE_USAGE_TRANSFER_SRC_BIT|VK_IMAGE_USAGE_TRANSFER_DST_BIT|VK_IMAGE_USAGE_SAMPLED_BIT);
        SpatialScaler baseline(vk,inputSize,outputSize,VK_FORMAT_R8G8B8A8_UNORM,
            ls::ScalingMethod::Mako,sharpness,std::nullopt);
        SpatialScaler fusion(vk,inputSize,outputSize,VK_FORMAT_R8G8B8A8_UNORM,
            ls::ScalingMethod::Mako,sharpness,std::nullopt);
        const std::array refs{std::cref(inputs[0]),std::cref(inputs[1]),std::cref(inputs[2])};
        fusion.configureDirectFrameGenerationInputs(vk,refs);
        require(fusion.directFrameGenerationInputCount()==3,"missing input bindings");
        const std::array duplicates{std::cref(inputs[0]),std::cref(inputs[0])};
        rejected([&]{fusion.configureDirectFrameGenerationInputs(vk,duplicates);});
        require(fusion.directFrameGenerationInputCount()==3,"failed replacement lost old bindings");
        for(unsigned phase=0;phase<6;++phase) {
            auto& input=inputs[phase%3];
            uploadImage(vk,input,pattern(inputSize,phase));
            blits=0;record(vk,baseline,input,baselineOutput);
            require(blits==2,"baseline copy count changed");
            blits=0;record(vk,fusion,input,fusionOutput,VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL);
            require(blits==1,"fusion did not remove exactly one input copy");
            require(download(vk,baselineOutput)==download(vk,fusionOutput),"fusion pixels differ");
            ++comparisons;
        }
        require(fusion.frameFusionRecordedFrames()==6,"recorded-frame counter incorrect");
        fusion.clearDirectFrameGenerationInputs();
        require(fusion.frameFusionRecordedFrames()==0,"clear retained stale evidence");
        blits=0;record(vk,fusion,inputs[0],fusionOutput,VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL);
        require(blits==2,"clearing did not restore copy path");
        const vk::Image wrongSize(vk,{inputSize.width+1,inputSize.height});
        const std::array wrongSizeRefs{std::cref(wrongSize)};
        rejected([&]{fusion.configureDirectFrameGenerationInputs(vk,wrongSizeRefs);});
        const vk::Image wrongFormat(vk,inputSize,VK_FORMAT_R16G16B16A16_SFLOAT);
        const std::array wrongFormatRefs{std::cref(wrongFormat)};
        rejected([&]{fusion.configureDirectFrameGenerationInputs(vk,wrongFormatRefs);});
        const vk::Image noSampling(vk,inputSize,VK_FORMAT_R8G8B8A8_UNORM,VK_IMAGE_USAGE_STORAGE_BIT);
        const std::array noSamplingRefs{std::cref(noSampling)};
        rejected([&]{fusion.configureDirectFrameGenerationInputs(vk,noSamplingRefs);});
        // An unregistered image must use the baseline; never reuse a descriptor
        // for another generated image merely because its dimensions match.
        fusion.configureDirectFrameGenerationInputs(vk,std::span(refs).first(1));
        blits=0;record(vk,fusion,inputs[1],fusionOutput,VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL);
        require(blits==2,"unregistered source was sampled through the wrong binding");
        SpatialScaler native(vk,inputSize,outputSize,VK_FORMAT_R8G8B8A8_UNORM,
            ls::ScalingMethod::Native,sharpness,std::nullopt);
        native.configureDirectFrameGenerationInputs(vk,refs);
        require(native.directFrameGenerationInputCount()==0,"native baseline advertised fusion");
    }
    std::cout << "Frame Fusion PASS: " << comparisons
        << " byte-identical image comparisons; input-copy elimination; rollback; invalid-input guards\n";
}
static void profile(vk::Vulkan& vk) {
    const VkExtent2D sourceSize{852,532},outputSize{1280,800};
    const vk::Image input(vk,sourceSize,VK_FORMAT_R8G8B8A8_UNORM,
        VK_IMAGE_USAGE_TRANSFER_SRC_BIT|VK_IMAGE_USAGE_TRANSFER_DST_BIT|VK_IMAGE_USAGE_SAMPLED_BIT);
    const vk::Image output(vk,outputSize,VK_FORMAT_R8G8B8A8_UNORM,
        VK_IMAGE_USAGE_TRANSFER_SRC_BIT|VK_IMAGE_USAGE_TRANSFER_DST_BIT|VK_IMAGE_USAGE_SAMPLED_BIT);
    for(const bool direct : {false,true}) {
        SpatialScaler scaler(vk,sourceSize,outputSize,VK_FORMAT_R8G8B8A8_UNORM,
            ls::ScalingMethod::Mako,0.5F,std::nullopt);
        if(direct) { const std::array refs{std::cref(input)};
            scaler.configureDirectFrameGenerationInputs(vk,refs); }
        uploadImage(vk,input,pattern(sourceSize,0));
        for(unsigned i=0;i<8;++i) record(vk,scaler,input,output,
            i==0 ? VK_IMAGE_LAYOUT_GENERAL : VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL);
        TimestampQueryPool queries(vk,80);
        const vk::CommandBuffer command(vk);command.begin(vk);queries.reset(command.handle());
        for(uint32_t i=0;i<40;++i) {
            queries.write(command.handle(),VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT,2*i);
            scaler.recordSourceToPresentation(vk,command,input.handle(),output.handle(),
                VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL,VK_IMAGE_LAYOUT_UNDEFINED,VK_IMAGE_LAYOUT_GENERAL);
            queries.write(command.handle(),VK_PIPELINE_STAGE_BOTTOM_OF_PIPE_BIT,2*i+1);
        }
        command.end(vk);command.submit(vk);
        auto samples=queries.microseconds();std::sort(samples.begin(),samples.end());
        std::cout << (direct ? "fusion" : "baseline") << " samples=40 gpu_median_us="
            << (samples[19]+samples[20])/2 << " gpu_p95_us=" << samples[37]
            << " blits_per_generated_frame=" << (direct ? 1 : 2) << '\n';
    }
    std::cout << "Timing describes this Vulkan device; it is not a Steam Deck energy measurement.\n";
}
int main(int argc,char** argv) {
    try {
        vk::Vulkan vk("gfg-frame-fusion-tests",{1,0,0},"gfg-frame-fusion-tests",{1,0,0},
            [](const vk::VulkanInstanceFuncs&,const std::vector<VkPhysicalDevice>& devices){
                if(devices.empty()) throw std::runtime_error("no Vulkan device");
                return devices.front();
            });
        auto& functions=const_cast<vk::VulkanDeviceFuncs&>(vk.df());
        originalBlit=functions.CmdBlitImage;functions.CmdBlitImage=countedBlit;
        if(argc==2 && std::string(argv[1])=="--profile") profile(vk);
        else integration(vk);
        functions.CmdBlitImage=originalBlit;
        return 0;
    } catch(const std::exception& error) {
        std::cerr << "Frame Fusion FAIL: " << error.what() << '\n';return 1;
    }
}
