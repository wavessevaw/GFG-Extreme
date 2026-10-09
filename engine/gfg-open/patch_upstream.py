#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
from pathlib import Path
import sys,shutil
root=Path(sys.argv[1]);here=Path(__file__).resolve().parent
backend=root/"engine/mako-backend"
shutil.copytree(here,backend/"src/gfg-open",dirs_exist_ok=True)
s=(backend/"src/mako.cpp").read_text()
def replace(old,new,count=1):
 global s
 assert s.count(old)==count,(old,s.count(old))
 s=s.replace(old,new)
replace('#include "helpers/temporal_phases.hpp"','#include "helpers/temporal_phases.hpp"\n#include "gfg-open/open_context.hpp"')
replace('return this->shaders;', 'return *this->shaders;')
replace('ShaderRegistry shaders;', 'std::optional<ShaderRegistry> shaders;\n    public:\n        bool usesOpen() const { return !shaders.has_value(); }')
a=s.index('    /// context class');b=s.index('\nInstance::Instance',a)
s=s[:a]+s[a:b].replace('ContextImpl','LegacyContextImpl')+s[b:]
s=s.replace('ContextImpl::ContextImpl(', 'LegacyContextImpl::LegacyContextImpl(')
s=s.replace('void Context::','void LegacyContextImpl::')
s=s.replace('bool Context::waitForIdle','bool LegacyContextImpl::waitForIdle')
replace('shaders(createShaderRegistry(this->vk, shaderDllPath,\n            allowLowPrecision && vk.supportsFP16()))',
'''shaders((std::getenv("GFG_OPEN_FG") && std::string(std::getenv("GFG_OPEN_FG")) == "1")
            ? std::nullopt : std::optional<ShaderRegistry>(createShaderRegistry(this->vk, shaderDllPath,
            allowLowPrecision && vk.supportsFP16())))''')
replace('    const auto& vk = this->m_impl->getVulkan();\n    constexpr VkImageUsageFlags usage',
        '    if (this->m_impl->usesOpen()) return false;\n    const auto& vk = this->m_impl->getVulkan();\n    constexpr VkImageUsageFlags usage')
replace('(this->m_impl->getShaderRegistry().is_fp16 ? "fp16" : "fp32")',
 '(this->m_impl->usesOpen() ? "open-fp32" : (this->m_impl->getShaderRegistry().is_fp16 ? "fp16" : "fp32"))')
point=s.index('\nInstance::Instance')
wrapper='''
namespace mako::backend {
class ContextImpl {
 std::unique_ptr<LegacyContextImpl> legacy;
 std::unique_ptr<gfg::OpenContext> open;
public:
 ContextImpl(const InstanceImpl& instance,ls::FileDescriptorScope& src,
  ls::FileDescriptorScope& dst,ls::FileDescriptorScope& sync,VkExtent2D extent,
  FrameEncoding encoding,float flow,bool perf) {
  if(instance.usesOpen()) open=std::make_unique<gfg::OpenContext>(
   instance.getVulkan(),src,dst,sync,extent,encoding);
  else legacy=std::make_unique<LegacyContextImpl>(
   instance,src,dst,sync,extent,encoding,flow,perf);
 }
 void scheduleFrames(){if(open)open->scheduleFrames();else legacy->scheduleFrames();}
 void scheduleFrames(std::span<const float> t){if(open)open->scheduleFrames(t);else legacy->scheduleFrames(t);}
 void scheduleFrameHistory(){if(open)open->scheduleFrameHistory();else legacy->scheduleFrameHistory();}
 bool waitForIdle(uint64_t timeout)const{return open?open->waitForIdle(timeout):legacy->waitForIdle(timeout);}
};
}
'''
s=s[:point]+wrapper+s[point:]
(backend/"src/mako.cpp").write_text(s)
cm=backend/"CMakeLists.txt"
c=cm.read_text().replace('"src/mako.cpp")','"src/gfg-open/open_context.cpp"\n    "src/mako.cpp")')
cm.write_text(c)
p=root/"engine/mako-render/src/instance.cpp";s=p.read_text()
old='''            else
                dll = ls::findShaderDll();'''
assert s.count(old)==1
s=s.replace(old,'''            else if (!(std::getenv("GFG_OPEN_FG") && std::string(std::getenv("GFG_OPEN_FG")) == "1"))
                dll = ls::findShaderDll();''')
p.write_text(s)
