"""Replay one recurring 28 FPS output pattern on every courtyard pair, reference slots fixed."""
import os, subprocess as sp
from pathlib import Path
import sys

bench,work=map(Path,sys.argv[1:]);bench=bench.resolve();work=work.resolve()
s=(bench/'engine/kfg_vktest.c').read_text()
old='kfg_plan_generate(&p, (uint32_t)w, (uint32_t)h, fa, fb, fb, (float)t, hold ? KFG_FLAG_VARIABLE_INTERVAL : 0);'
assert s.count(old)==1
new="""// Fractions emitted for the first changed 28 FPS pair by phase_trace.c.
                    const int balanced = getenv("BALANCED_PHASE") != NULL;
                    const double sampled = mode == 2 ? (balanced ? 0.5 : 5.0/12.0) :
                        (j == 1 ? 0.25 : balanced ? 5.0/8.0 : 9.0/16.0);
                    """+old.replace('(float)t','(float)sampled')
(work/'phase_replay.c').write_text(s.replace(old,new))
exe=work/'phase-replay'
sp.run(['cc','-O2','-std=c11','-I'+str(bench/'engine'),work/'phase_replay.c',bench/'engine/kfg_vk.c','-lvulkan','-lm','-o',exe],check=True)
for side in ['old','new','new2','old2']:
 out=work/('pixels-'+side);out.mkdir(exist_ok=True)
 env=dict(os.environ,KFG_HARD_X2='1',KFG_DETAIL_SEQUENCE_OUT=str(out),KFG_COURTYARD_TIMING='1')
 if side.startswith('new'):env['BALANCED_PHASE']='1'
 with (out/'time.log').open('w') as log:
  sp.run([exe,'--hard','--size','1280x800','--scene','h_courtyard_reversal','--spv',bench/'build','--json',out/'results.json'],env=env,stdout=log,check=True)
 print(side,flush=True)
