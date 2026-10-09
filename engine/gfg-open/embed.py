#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
from pathlib import Path
import subprocess,struct
here=Path(__file__).resolve().parent
out=["// Generated from GPL-3.0-or-later GLSL; do not edit.",
     "#pragma once","#include <array>","#include <cstdint>","namespace gfg::embedded {"]
for name in ("flow","refine","compose"):
 spv=here/(name+".spv")
 subprocess.run(["glslangValidator","-V","--target-env","vulkan1.1","-o",str(spv),str(here/"shaders"/(name+".comp"))],check=True)
 subprocess.run(["spirv-val","--target-env","vulkan1.1",str(spv)],check=True)
 data=spv.read_bytes();words=struct.unpack("<"+"I"*(len(data)//4),data)
 out.append("inline constexpr std::array<uint32_t,%d> %s = {%s};"%(len(words),name,",".join("0x%x"%w for w in words)))
out.append("}")
(here/"embedded.hpp").write_text("\n".join(out)+"\n")
