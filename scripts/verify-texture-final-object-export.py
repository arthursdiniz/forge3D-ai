"""Export a fresh immutable version of the validated two-material QA object."""
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.app import create_app
from backend.worker import Worker
from fastapi.testclient import TestClient
qa=ROOT/'data/texture-engine-20261012'
app=create_app(qa/'object-flow/store',start_worker=False);client=TestClient(app)
response=client.post('/api/jobs/48e5737459c54ab0876e55c0051b1d02/export',json={'pipeline':'URP'})
assert response.status_code==201,response.text
job=response.json();Worker(ROOT,app.state.store).process_job(job)
result=app.state.store.get(job['id']);assert result['status']=='completed',result
folder=app.state.store.directory(job['id'])/'Forge3D_Asset'
paths=[]
for line in (folder/'Models/Model.mtl').read_text().splitlines():
    if line.lstrip().startswith('map_'):
        uri=line.split()[-1];path=(folder/'Models'/uri).resolve()
        assert path.is_file() and path.is_relative_to(folder.resolve()),uri
        paths.append(uri)
(qa/'final-object-export.json').write_text(json.dumps({'job':result,'package':str(folder),'obj_maps_verified':paths},indent=2),encoding='utf-8')
print('FINAL_OBJECT_EXPORT_MAPS_PASS '+job['id'],flush=True)
