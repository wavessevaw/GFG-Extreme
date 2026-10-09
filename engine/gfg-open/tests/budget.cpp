// SPDX-License-Identifier: GPL-3.0-or-later
#include "../budget.hpp"
#include <cassert>
#include <limits>
int main(){
 gfg::GpuBudget sustained;
 for(int i=0;i<6;i++)sustained.observe(7);
 assert(sustained.bypass);
 sustained.observe(1);assert(sustained.bypass);
 gfg::GpuBudget healthy;
 for(int i=0;i<240;i++)healthy.observe(1.2);
 assert(!healthy.bypass);
 healthy.observe(10);healthy.observe(10);healthy.observe(1);
 healthy.observe(10);healthy.observe(10);assert(!healthy.bypass);
 healthy.observe(std::numeric_limits<double>::quiet_NaN());assert(!healthy.bypass);
 healthy.observe(10);assert(healthy.bypass);
}
