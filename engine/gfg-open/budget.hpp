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
 double currentLimitMs=limitMs;
 double cadenceSamples[7]{};
 unsigned cadenceCount=0,cadenceIndex=0;
 double recoveryThresholdMs() const { return currentLimitMs*.75; }
 void sourceInterval(double ms){
  // Menus, source stalls and single wake-ups cannot inflate the allowance.
  if(!std::isfinite(ms)||ms<8.0||ms>50.0)return;
  cadenceSamples[cadenceIndex++%7]=ms;
  if(cadenceCount<7)++cadenceCount;
  if(cadenceCount<5)return;
  double sorted[7];for(unsigned i=0;i<cadenceCount;++i)sorted[i]=cadenceSamples[i];
  for(unsigned i=1;i<cadenceCount;++i)for(unsigned j=i;j>0&&sorted[j]<sorted[j-1];--j){double t=sorted[j];sorted[j]=sorted[j-1];sorted[j-1]=t;}
  // Quarter of the source period, never more than 8 ms per entire pair.
  const double period=sorted[cadenceCount/2];
  currentLimitMs=std::fmin(8.0,std::fmax(2.0,period*.25));
 }
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
   if(ms>recoveryThresholdMs()){
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
  overruns=ms>currentLimitMs?overruns+1:0;
  if(overruns>=3){
   bypass=true;probing=false;goodProbes=0;cooldownFrames=initialCooldownFrames;
  }
 }
};
} // namespace gfg
