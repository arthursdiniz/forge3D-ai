"""Real static GLTF-sidecar and FBX-sidecar import proof in a separate QA store."""
import hashlib
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import trimesh
from fastapi.testclient import TestClient
from backend.app import create_app
from backend.worker import Worker
from backend.texture_engine.identity import compare_geometry
qa=ROOT/'data/texture-engine-20261012/import-formats-final'
qa.mkdir(parents=True,exist_ok=False)
source=ROOT/'data/texture-engine-20261012/object-flow/store/assets/68c9f787891f4fffa3f5c8f0d72a9dce/Forge3D_Asset'
scene=trimesh.load(source/'Models/Model.glb',force='scene',process=False)
resources=scene.export(file_type='gltf',include_normals=True)
gltf_name=next(name for name in resources if name.endswith('.gltf'))
app=create_app(qa/'store',start_worker=False);client=TestClient(app);worker=Worker(ROOT,app.state.store)
results={}
for kind,name,payload,sidecars in [
    ('gltf',gltf_name,resources[gltf_name],{name:body for name,body in resources.items() if name!=gltf_name}),
    ('fbx','object.fbx',(source/'Models/Model.fbx').read_bytes(),{path.name:path.read_bytes() for path in (source/'Textures').glob('*.png')})
]:
    files=[('model',(name,payload,'application/octet-stream'))]+[('sidecars',(key,body,'application/octet-stream')) for key,body in sidecars.items()]
    response=client.post('/api/models/import',files=files);assert response.status_code==201,response.text
    job=response.json();worker.process_job(job);result=app.state.store.get(job['id']);assert result['status']=='completed',result
    folder=app.state.store.directory(job['id'])
    comparison=compare_geometry(scene,trimesh.load(folder/'model.glb',force='scene',process=False));assert comparison['equivalent'],comparison
    assert hashlib.sha256((folder/'uploads'/name).read_bytes()).digest()==hashlib.sha256(payload).digest()
    results[kind]={'job':job['id'],'sidecars':list(sidecars),'original_preserved':True,'world_geometry':comparison,'import':result['metadata']['import']}
    print(kind+' STATIC_IMPORT_PASS',flush=True)
(qa/'result.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
