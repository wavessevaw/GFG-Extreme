from pathlib import Path
from urllib.request import urlopen
import hashlib, io, zipfile
root=Path.cwd()
url='https://github.com/wavessevaw/GFG-Extreme/releases/download/v3.4.4/'
name='GFG-Extreme-v3_4_4.zip'
data=urlopen(url+name,timeout=60).read()
expected=urlopen(url+'SHA256SUMS.txt',timeout=30).read().decode().split()[0]
assert hashlib.sha256(data).hexdigest()==expected
files='py_modules/gfg_plugin/resource_optimizer.py py_modules/gfg_plugin/plugin.py py_modules/gfg_plugin/service.py py_modules/gfg_plugin/settings.py py_modules/gfg_plugin/paths.py package.json package-lock.json dist/index.js RESOURCE_OPTIMIZER.md'.split()
out=Path('GFG-Extreme-3.4.4-resource.2.zip')
with zipfile.ZipFile(io.BytesIO(data)) as src, zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as dst:
 for i in src.infolist():
  rel=i.filename.removeprefix('GFG-Extreme/')
  dst.writestr(i,(root/rel).read_bytes() if rel in files else src.read(i))
 for rel in files:
  if 'GFG-Extreme/'+rel not in dst.namelist():dst.write(root/rel,'GFG-Extreme/'+rel)
with zipfile.ZipFile(out) as z:assert z.testzip() is None
print(hashlib.sha256(out.read_bytes()).hexdigest(),out)
