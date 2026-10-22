"""Read-only audit probes; fixtures live in temporary directories, no system installation."""
import sys, json, importlib.util
from pathlib import Path
root=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else Path("/workspace/gfg-300-audit")
sys.path[:0]=[str(root/'source/py_modules'),str(root/'source/tests')]
from gfg_plugin.kedavra.ctl import Control
from gfg_plugin.kedavra.install import bench
from gfg_plugin.kedavra.hud import live_for
from test_kedavra_install import InstallerTest
out={}
p=root/'probe.csv';p.write_text('vblank,flip_ns\n')
pkg=root/'package/GFG-Extreme'
out['packaged_analysis']=Control('/tmp',pkg).analyze(str(p))
out['packaged_benchmark']=bench(pkg,root/'probe-bench')
out['half_refresh_health']=live_for({'state':'active'},dict(flips=45.,sources=30.,real=30.,gen=60.,repeat=0.))
x=InstallerTest();x.setUp()
try:
 x.inst.install();(x.inst.runtime/'VERSION').write_text('previous-working')
 original=x.inst.run
 def fail(argv,**kw):return (1,'injected setcap failure') if argv[0]=='setcap' else original(argv,**kw)
 x.inst.run=fail
 try:x.inst.install()
 except RuntimeError as e:out['failed_update_error']=str(e)
 out['failed_update_retained_old_version']=x.inst.installed_version()=='previous-working'
finally:x.tearDown()
spec=importlib.util.spec_from_file_location('pacing',root/'kedavra/kedavra/tools/kfg_pacing.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
rows=[]
for i in range(400):
 rows.append(dict(flip_ns=str(i*22222222),refresh_ns='11111111',kind='real',reason='',state='active',content=str(i),vblank=str(i*2),src_a=str(i),src_b='0',phase_num='0',phase_den='0',delay='0',mult='3'))
r=m.analyze(rows,skip_s=0)
out['45_flips_at_90hz_analyzer']={k:r[k] for k in ('missed_fraction','interval_error_ms','checks','pass')}
(root/'reproductions.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
