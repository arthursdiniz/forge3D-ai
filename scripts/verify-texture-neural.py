"""Real neural end-to-end trial. No mocked inference and no automatic proof publication."""
import json
import shutil
import subprocess
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
target=ROOT/'data/texture-engine-20261012/neural-hinata-trial1'
target.mkdir(parents=True,exist_ok=True)
reference=target/'references/front';reference.mkdir(parents=True,exist_ok=True)
shutil.copy2(ROOT/'data/test-inputs/hinata-shoyo-reference-20261011.png',reference/'source.png')
(target/'texture_references.json').write_text(json.dumps({'views':{'front':{'path':'references/front/source.png'}}}),encoding='utf-8')
(target/'options.json').write_text(json.dumps({'provider':'neural_multiview','resolution':1024,'front_axis':'negative_y','uv_mode':'preserve','prompt':'anime volleyball player, orange hair, black and orange volleyball uniform, number 10','style':'anime','seed':44}),encoding='utf-8')
source=ROOT/'data/assets/d50d2f098559482ca796bb59672b7289/model.glb'
with (target/'trial.log').open('a',encoding='utf-8') as log:
    result=subprocess.run([str(ROOT/'.venv-texture/Scripts/python.exe'),str(ROOT/'backend/texture_engine/cli.py'),'--input',str(source),'--output',str(target),'--options',str(target/'options.json')],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
assert result.returncode==0,'Neural trial failed: see '+str(target/'trial.log')
report=json.loads((target/'texture.json').read_text(encoding='utf-8'))
assert report['geometry']['equivalent'] and report['synthesized_percent']>30
assert report['neural']['offline'] and report['neural']['joint_views']==6
print(json.dumps(report['neural'],indent=2))
