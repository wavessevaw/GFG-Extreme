// SPDX-License-Identifier: GPL-3.0-or-later
#pragma once
#include <cmath>
namespace gfg {
// Measures GPU execution, never CPU waiting or the game's frame interval.
// A context stays in real-frame passthrough after repeated budget overruns.
struct GpuBudget {
 unsigned samples=0,overruns=0;
 bool bypass=false;
 static constexpr double limitMs=4.0;
 void observe(double ms){
  if(!std::isfinite(ms)||ms<0)return;
  ++samples;
  if(samples<=3)return;
  overruns=ms>limitMs?overruns+1:0;
  if(overruns>=3)bypass=true;
 }
};
}
