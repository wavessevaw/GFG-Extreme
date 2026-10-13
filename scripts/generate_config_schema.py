#!/usr/bin/env python3
"""Regenerate schema-owned declarations while retaining the wrapper helper body."""
import ast
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from shared_config import CONFIG_SCHEMA_DEF

target = ROOT / 'py_modules/gfg_plugin/config_schema_generated.py'
source = target.read_text(encoding='utf-8')
lines = source.splitlines(keepends=True)
tree = ast.parse(source)
types = {'boolean':'bool','integer':'int','float':'float','string':'str'}
edits = []
constants = [n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id.isupper() and t.id != 'ALL_FIELDS' for t in n.targets)]
edits.append((constants[0].lineno-1, constants[-1].end_lineno,
              ''.join(f'{key.upper()} = "{key}"\n' for key in CONFIG_SCHEMA_DEF)))
for node in tree.body:
    if isinstance(node,ast.ClassDef) and node.name in ('ConfigurationData','ConfigurationPatch','WrapperSettingsData'):
        fields = CONFIG_SCHEMA_DEF if node.name != 'WrapperSettingsData' else {k:v for k,v in CONFIG_SCHEMA_DEF.items() if v['location']=='script'}
        # Preserve existing inheritance/total argument and documentation.
        header=lines[node.lineno-1]
        body = header + '    """Schema fields generated from shared_config.py."""\n'
        body += ''.join(f'    {key}: {types[value["fieldType"].value]}\n' for key,value in fields.items())
        edits.append((node.lineno-1,node.end_lineno,body))
    if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id == 'ALL_FIELDS' for t in node.targets):
        edits.append((node.lineno-1,node.end_lineno,'ALL_FIELDS = '+repr(list(CONFIG_SCHEMA_DEF))+'\n'))
for start,end,content in sorted(edits,reverse=True): lines[start:end]=[content]
target.write_text(''.join(lines),encoding='utf-8',newline='\n')
print(f'Generated {len(CONFIG_SCHEMA_DEF)} fields')
