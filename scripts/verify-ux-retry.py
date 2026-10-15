"""Actual CPU projection/preview retry with a deliberate inspection-stage fault, isolated store."""
import hashlib,json,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from fastapi.testclient import TestClient
from backend.app import create_app
from backend.worker import Worker
QA=ROOT/'data/ux-upgrade-20261015';folder=QA/'retry-flow';assert not folder.exists()
app=create_app(folder,start_worker=False);store=app.state.store;client=TestClient(app)
original=ROOT/'data/assets'/(QA/'e2e-model-id.txt').read_text().strip()/'model.glb'
source_hash=hashlib.sha256(original.read_bytes()).hexdigest()
parent=store.create('Imported real Hinata geometry','imported',{},kind='import')
shutil.copy2(original,store.directory(parent['id'])/'model.glb')
store.update(parent['id'],status='completed',metadata={'render_front_axis':'negative_y'},artifacts={'model':'/isolated-source.glb'})
payload=(ROOT/'data/test-inputs/hinata-shoyo-reference-20261011.png').read_bytes()
response=client.post('/api/workflows/'+parent['id']+'/texture',data={'options':json.dumps({'provider':'reference_projection','quality':'fast','use_saved_references':False})},files={'front':('reference.png',payload,'image/png')})
assert response.status_code==201,response.text
first=response.json();worker=Worker(ROOT,store);real_blender=worker.blender
def injected_fault(*args,**kwargs):raise RuntimeError('QA deliberate inspection failure after a validated base')
worker.blender=injected_fault
try:worker.process_job(first)
except RuntimeError as error:store.update(first['id'],status='failed',error=str(error))
else:raise AssertionError('Fault injection did not execute.')
first_dir=store.directory(first['id']);assert (first_dir/'base/stage-cache.json').is_file()
first_model_hash=hashlib.sha256((first_dir/'base/model.glb').read_bytes()).hexdigest()
response=client.post('/api/workflows/'+first['id']+'/retry');assert response.status_code==201,response.text
second=response.json();worker.blender=real_blender;worker.process_job(second)
after=store.get(second['id']);assert after['status']=='completed'
assert after['metadata']['workflow']['cache_reused'] is True
assert store.get(first['id'])['status']=='failed'
assert hashlib.sha256((first_dir/'base/model.glb').read_bytes()).hexdigest()==first_model_hash
assert hashlib.sha256(original.read_bytes()).hexdigest()==source_hash
(QA/'retry-validation.json').write_text(json.dumps({'passed':True,'scope':'Actual projection, masks/optional refinement and Blender inspection in isolated store; deliberate first inspection failure. Neural inference was not rerun in this cache test.',
    'first':first['id'],'retry':second['id'],'cache_reused':True,'result':after,'original_sha256':source_hash},indent=2),encoding='utf-8')
print('REAL_VALIDATED_BASE_RETRY_PASS',flush=True)
