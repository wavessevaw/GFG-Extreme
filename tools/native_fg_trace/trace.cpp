// SPDX-License-Identifier: GPL-3.0-or-later
// Harness wiring follows MAKO's GPL host context. Shaderchain implementations
// and helpers are compiled from the supplied checkout, without modifications.
#include "sim.hpp"
#include "shaderchains/mipmaps.hpp"
#include "shaderchains/alpha0.hpp"
#include "shaderchains/alpha1.hpp"
#include "shaderchains/beta0.hpp"
#include "shaderchains/beta1.hpp"
#include "shaderchains/gamma0.hpp"
#include "shaderchains/gamma1.hpp"
#include "shaderchains/delta0.hpp"
#include "shaderchains/delta1.hpp"
#include "shaderchains/generate.hpp"
#include "helpers/temporal_phases.hpp"
#include <cstdlib>

using namespace mako::backend;
struct Pass {
    std::vector<Gamma0> gamma0;
    std::vector<Gamma1> gamma1;
    std::vector<Delta0> delta0;
    std::vector<Delta1> delta1;
    std::optional<Generate> generate;
};
int main(int argc, char** argv) {
    if (argc!=6) return 2;
    const unsigned w=std::stoul(argv[1]), h=std::stoul(argv[2]);
    const unsigned n=std::stoul(argv[3]);
    const bool perf=std::stoi(argv[4])!=0;
    const float scale=std::stof(argv[5]);
    if (!w||!h||n<1||n>4||scale<0.25||scale>1) return 2;
    vk::Vulkan vk;
    ShaderRegistry shaders{};
    shaders.mipmaps.name="mipmaps"; shaders.generate.name="generate";
    for (auto* group : {&shaders.quality,&shaders.performance}) {
        for(size_t i=0;i<group->alpha.size();++i) group->alpha[i].name="alpha"+std::to_string(i);
        for(size_t i=0;i<group->beta.size();++i) group->beta[i].name="beta"+std::to_string(i);
        for(size_t i=0;i<group->gamma.size();++i) group->gamma[i].name="gamma"+std::to_string(i);
        for(size_t i=0;i<group->delta.size();++i) group->delta[i].name="delta"+std::to_string(i);
    }
    Ctx ctx{.vk=std::cref(vk),.shaders=std::cref(shaders),
        .imageMemoryPool=std::make_shared<vk::ImageMemoryPool>(),
        .pool={},.constantBuffer={},.constantBuffers=std::vector<vk::Buffer>(n),
        .bnbSampler={},.bnwSampler={},.eabSampler={},.sourceExtent={w,h},
        .flowExtent={unsigned(w*scale),unsigned(h*scale)},
        .highPrecision=false,.hdr=false,.flow=1/scale,.perf=perf,.count=n};
    auto image=[&](VkExtent2D size){return vk::Image(vk,size,ctx.imageMemoryPool);};
    sim::owner="external-source";
    std::pair<vk::Image,vk::Image> sources{image({w,h}),image({w,h})};
    sim::owner="black"; auto black=image({1,1});
    sim::owner="external-output"; std::vector<vk::Image> outputs;
    outputs.reserve(n); for(unsigned i=0;i<n;++i) outputs.push_back(image({w,h}));
    sim::owner="prepass-mipmaps"; Mipmaps mipmaps(ctx,sources);
    std::vector<Alpha0> a0; a0.reserve(7);
    std::vector<Alpha1> a1; a1.reserve(7);
    for(unsigned i=0;i<7;++i){sim::owner="prepass-alpha0";a0.emplace_back(ctx,mipmaps.getImages().at(i));}
    for(unsigned i=0;i<7;++i){sim::owner="prepass-alpha1";a1.emplace_back(ctx,alphaHistoryCounts.at(i),a0.at(i).getImages());}
    sim::owner="prepass-beta0";Beta0 b0(ctx,a1.at(0).getImages());
    sim::owner="prepass-beta1";Beta1 b1(ctx,b0.getImages());
    std::vector<Pass> passes;passes.reserve(n);
    for(unsigned i=0;i<n;++i){
        auto& p=passes.emplace_back();p.gamma0.reserve(7);p.gamma1.reserve(7);p.delta0.reserve(3);p.delta1.reserve(3);
        for(unsigned j=0;j<7;++j){
            sim::owner="output"+std::to_string(i)+"-gamma0";
            p.gamma0.emplace_back(ctx,i,a1.at(6-j).getImages(),j? p.gamma1.at(j-1).getImage():black);
            sim::owner="output"+std::to_string(i)+"-gamma1";
            p.gamma1.emplace_back(ctx,i,p.gamma0.at(j).getImages(),a0.at(6-j).getImages(),
                j?p.gamma1.at(j-1).getImage():black,b1.getImages().at(j?6-j:5));
            if(j>=4){
                sim::owner="output"+std::to_string(i)+"-delta0";
                p.delta0.emplace_back(ctx,i,a1.at(6-j).getImages(),p.gamma0.at(j).getImages(),
                    p.gamma1.at(j).getTempImages0(),j==4?black:p.delta1.at(j-5).getImage0(),p.gamma1.at(j-1).getImage());
                sim::owner="output"+std::to_string(i)+"-delta1";
                p.delta1.emplace_back(ctx,i,p.gamma0.at(j).getImages(),p.gamma1.at(j).getTempImages0(),
                    p.gamma1.at(j).getTempImages1(),j==4?black:p.delta1.at(j-5).getImage0(),
                    b1.getImages().at(6-j),j==4?black:p.delta1.at(j-5).getImage1());
            }
        }
        p.generate.emplace(ctx,i,sources,p.gamma1.at(6).getImage(),p.delta1.at(2).getImage0(),p.delta1.at(2).getImage1(),outputs.at(i));
    }
    vk::CommandBuffer cmd;
    // Execute six temporal phases; allocation and bindings are the actual host
    // chain code. All operations below are recorded, never executed by a GPU.
    for(unsigned frame=0;frame<7;++frame){
        sim::frame=frame;
        sim::phase="prepass";sim::pass=frame;
        mipmaps.render(vk,cmd,frame);
        for(unsigned j=0;j<7;++j){a0.at(6-j).render(vk,cmd);a1.at(6-j).render(vk,cmd,frame);}
        b0.render(vk,cmd,frame);b1.render(vk,cmd);
        sim::phase="synthesis";
        for(unsigned i=0;i<n;++i){sim::pass=i;auto& p=passes.at(i);
            for(unsigned j=0;j<7;++j){p.gamma0.at(j).render(vk,cmd,frame);p.gamma1.at(j).render(vk,cmd);
                if(j>=4){p.delta0.at(j-4).render(vk,cmd,frame);p.delta1.at(j-4).render(vk,cmd);}}
            p.generate->render(vk,cmd,frame);
        }
    }
}
