// SPDX-License-Identifier: GPL-3.0-or-later
#pragma once
#include <cmath>
namespace gfg {
// Only actual GPU execution is sampled: never CPU waits or output cadence.
// A budget trip temporarily bypasses interpolation. Bypass samples cannot
// count as proof that synthesis is cheap: recovery must execute real probes.
struct GpuBudget {
 unsigned samples=0,overruns=0;
 unsigned cooldownFrames=0,goodProbes=0,failedProbes=0,probeAttempts=0,recoveries=0;
 bool bypass=false,probing=false,permanent=false;
 static constexpr double limitMs=4.0;
 static constexpr double recoveryLimitMs=3.0;
 static constexpr unsigned initialCooldownFrames=300;
 static constexpr unsigned maxCooldownFrames=1800;
 bool passthrough() const { return bypass && !probing; }
 void disableWithoutTiming(){
  bypass=true;probing=false;permanent=true;cooldownFrames=0;
 }
 void beforeFrame(){
  if(!bypass||permanent||probing)return;
  if(cooldownFrames && --cooldownFrames)return;
  probing=true;goodProbes=0;++probeAttempts;
 }
 void observe(double ms){
  if(!std::isfinite(ms)||ms<0)return;
  ++samples;
  if(bypass){
   // 0.2 ms of bypass composition says nothing about the cost of optical flow.
   if(!probing||permanent)return;
   if(ms>recoveryLimitMs){
    probing=false;goodProbes=0;
    if(failedProbes<3)++failedProbes;
    unsigned delay=initialCooldownFrames<<failedProbes;
    cooldownFrames=delay>maxCooldownFrames?maxCooldownFrames:delay;
   }else if(++goodProbes>=3){
    bypass=false;probing=false;overruns=0;failedProbes=0;cooldownFrames=0;
    ++recoveries;
   }
   return;
  }
  if(samples<=3)return;
  overruns=ms>limitMs?overruns+1:0;
  if(overruns>=3){
   bypass=true;probing=false;goodProbes=0;cooldownFrames=initialCooldownFrames;
  }
 }
};
} // namespace gfg
