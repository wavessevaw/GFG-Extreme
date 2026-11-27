from pathlib import Path
import subprocess as sp
src=Path('phase_replay.c').read_text()
mark='if (timing) log_dispatch_times(e, &p);\n\t\t\t\t\tkfg_vk_download_rgba8'
i=src.index('const double sampled ='); prefix,src=src[:i],src[i:]
end=src.index('kfg_vk_download_rgba8'); start=src.rindex('if (timing)',0,end); mark=src[start:end]+ 'kfg_vk_download_rgba8'
src=src.replace(mark,'''if (timing) {
                        for (unsigned rep = 0; rep < 8; ++rep) {
                            bool new_phase = ((rep % 4 == 1 || rep % 4 == 2) != (f % 2 == 1));
                            double phase = mode == 2 ? (new_phase ? .5 : 5.0/12.0) :
                                           (j == 1 ? .25 : new_phase ? 5.0/8.0 : 9.0/16.0);
                            kfg_plan_generate(&p,w,h,fa,fb,fb,(float)phase,hold ? KFG_FLAG_VARIABLE_INTERVAL : 0);
                            run_plan(e,&p,NULL,NULL);
                            printf("pairtime %d %d %d %d ",mode,f,j,(int)new_phase);
                            log_dispatch_times(e,&p);
                        }
                    }
                    kfg_vk_download_rgba8''',1)
Path('timed.c').write_text(prefix+src)
sp.run(['cc','-O2','-std=c11','-Isrc/kedavra/engine','timed.c','src/kedavra/engine/kfg_vk.c','-lvulkan','-lm','-o','timed'],check=True)
