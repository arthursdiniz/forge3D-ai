"""Actual SDXL text+geometry adapter test on an independently imported object."""
import json
import subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
record=json.loads((ROOT/'data/texture-engine-20261012/object-flow/result.json').read_text(encoding='utf-8'))
source=ROOT/'data/texture-engine-20261012/object-flow/store/assets'/record['import']/'model.glb'
target=ROOT/'data/texture-engine-20261012/neural-object-text-trial1';target.mkdir(parents=True,exist_ok=True)
(target/'texture_references.json').write_text(json.dumps({'views':{}}),encoding='utf-8')
(target/'options.json').write_text(json.dumps({'provider':'neural_multiview','conditioning':'text','prompt':'a two part game prop, larger red painted wooden block next to a smaller brushed steel block, coherent surface colors, no text','resolution':1024,'uv_mode':'preserve','front_axis':'negative_y','style':'stylized','seed':21}),encoding='utf-8')
with (target/'trial.log').open('a',encoding='utf-8') as log:
    result=subprocess.run([str(ROOT/'.venv-texture/Scripts/python.exe'),str(ROOT/'backend/texture_engine/cli.py'),'--input',str(source),'--output',str(target),'--options',str(target/'options.json')],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
assert result.returncode==0,'Text neural trial failed: '+str(target/'trial.log')
report=json.loads((target/'texture.json').read_text(encoding='utf-8'))
assert report['geometry']['equivalent'] and len(report['materials'])==2 and report['neural']['joint_views']==6 and report['neural']['offline']
print(json.dumps(report['neural'],indent=2))
