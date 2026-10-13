/* Compare actual scheduler implementations on the same deterministic workload. */
#include "../engine/gfg-pacer/src/scheduler.h"
#include <stdio.h>
#include <string.h>
int main(int argc,char**argv){
 gfg_policy p;gfg_sched s;gfg_policy_defaults(&p);
 p.real_target_hz=30;p.tick_shaping=0;p.stall_shield=0;
 gfg_sched_init(&s,&p);long long now=1000000000,began=now;
 for(int i=0;i<1000;i++)now=gfg_sched_present(&s,now+34000000);
 double fps=1000e9/(double)(now-began);
 printf("%s: 34 ms work under 30 Hz policy -> %.3f real FPS (simulation)\n",argc>1?argv[1]:"scheduler",fps);
 return argc>1&&!strcmp(argv[1],"fixed")&&fps<29;
}
