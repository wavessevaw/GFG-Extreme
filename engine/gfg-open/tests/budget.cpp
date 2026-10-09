// SPDX-License-Identifier: GPL-3.0-or-later
#include "../budget.hpp"
#include <cassert>
#include <limits>
int main(){
 gfg::GpuBudget healthy;
 for(int i=0;i<250;i++){healthy.beforeFrame();healthy.observe(1.2);}
 assert(!healthy.bypass);
 healthy.observe(10);healthy.observe(10);healthy.observe(1);
 healthy.observe(10);healthy.observe(10);assert(!healthy.bypass);
 healthy.observe(std::numeric_limits<double>::quiet_NaN());assert(!healthy.bypass);
 healthy.observe(10);assert(healthy.bypass&&healthy.passthrough());
 // Cheap passthrough work cannot unlock expensive frame generation.
 for(unsigned i=0;i<gfg::GpuBudget::initialCooldownFrames-1;i++){
  healthy.beforeFrame();assert(healthy.passthrough());healthy.observe(.24);
 }
 assert(healthy.probeAttempts==0);
 healthy.beforeFrame();assert(healthy.probing&&!healthy.passthrough());
 healthy.observe(2.3);healthy.beforeFrame();healthy.observe(2.0);
 assert(healthy.bypass&&healthy.probing);
 healthy.beforeFrame();healthy.observe(1.8);
 assert(!healthy.bypass&&!healthy.probing&&healthy.recoveries==1);
 // Sustained expensive probes back off; don't oscillate every frame.
 gfg::GpuBudget expensive;
 for(int i=0;i<6;i++)expensive.observe(7);
 assert(expensive.passthrough());
 for(unsigned i=0;i<gfg::GpuBudget::initialCooldownFrames;i++)expensive.beforeFrame();
 assert(expensive.probing);
 expensive.observe(7);
 assert(expensive.passthrough()&&expensive.cooldownFrames==600);
 for(unsigned i=0;i<600;i++){expensive.beforeFrame();if(i<599)assert(expensive.passthrough());}
 assert(expensive.probing&&expensive.probeAttempts==2);
 expensive.observe(8);assert(expensive.cooldownFrames==1200);
 // No timestamp support is fail-closed, with no unsafe reprobes.
 gfg::GpuBudget unavailable;
 unavailable.disableWithoutTiming();
 for(int i=0;i<10000;i++){unavailable.beforeFrame();unavailable.observe(.1);}
 assert(unavailable.passthrough()&&unavailable.probeAttempts==0);
}
