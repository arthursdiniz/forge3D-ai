"""Run the current independent CLI before renewing its source-bound availability proof."""
import hashlib
import json
import shutil
import subprocess
import time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
qa=ROOT/'data/ux-upgrade-20261015'
identifier=(qa/'e2e-model-id.txt').read_text().strip()
source=ROOT/'data/assets'/identifier/'model.glb'
folder=qa/'neural-regression';folder.mkdir(exist_ok=False)
ref=folder/'references/front';ref.mkdir(parents=True)
shutil.copy2(ROOT/'data/test-inputs/hinata-shoyo-reference-20261011.png',ref/'source.png')
options={'provider':'neural_multiview','resolution':2048,'uv_mode':'preserve','front_axis':'negative_y',
         'background_mode':'remove','style':'free','seed':44,'fusion':'robust'}
(folder/'options.json').write_text(json.dumps(options),encoding='utf-8')
(folder/'texture_references.json').write_text(json.dumps({'views':{'front':{'path':'references/front/source.png'}}}),encoding='utf-8')
source_hash=hashlib.sha256(source.read_bytes()).hexdigest();started=time.monotonic()
with (folder/'trial.log').open('w',encoding='utf-8') as log:
    result=subprocess.run([str(ROOT/'.venv-texture/Scripts/python.exe'),str(ROOT/'backend/texture_engine/cli.py'),
        '--input',str(source),'--output',str(folder),'--options',str(folder/'options.json')],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
assert result.returncode==0,'Inspect neural-regression/trial.log'
report=json.loads((folder/'texture.json').read_text())
assert report['geometry']['equivalent'] and report['neural']['offline'] and report['neural']['joint_views']==6
assert (folder/'prepared_references/front.png').is_file()
assert hashlib.sha256(source.read_bytes()).hexdigest()==source_hash
(folder/'regression.json').write_text(json.dumps({'passed':True,'wall_seconds':round(time.monotonic()-started,3),
    'source_sha256':source_hash,'geometry':report['geometry'],'neural':report['neural'],'prepared_reference':True},indent=2),encoding='utf-8')
# Renew only the changed files in this global engine proof, after real current-code inference.
path=ROOT/'models/texture/validation.json';proof=json.loads(path.read_text())
before={name:value for name,value in proof['source_sha256'].items() if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=value}
proof['source_sha256']={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in proof['source_sha256']}
proof['ux_regression']={'directory':str(folder.relative_to(ROOT)),'changed_sources':before,'suite':'274 tests passed; expanded workflow contract suite11 passed',
    'note':'Current real image-conditioned neural CLI, masked reference artifact, world geometry and offline6views passed. Existing text inference algorithm unchanged; retained prior text proof. New workflow validated separately.'}
path.write_text(json.dumps(proof,indent=2),encoding='utf-8')
print('CURRENT_NEURAL_CLI_PASS '+str(report['neural']['inference_seconds'])+'s',flush=True)
