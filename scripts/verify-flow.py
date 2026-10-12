"""Real API flow verification. No mocked generator. Requires running Forge3D."""
import hashlib
import json
import time
import zipfile
from pathlib import Path
import httpx

ROOT=Path(__file__).resolve().parents[1]
client=httpx.Client(base_url='http://127.0.0.1:8000',timeout=30)

def ready(job):
    identifier=job['id']
    deadline=time.monotonic()+600
    while time.monotonic()<deadline:
        job=client.get('/api/jobs/'+identifier).raise_for_status().json()
        if job['status']=='completed':
            return job
        if job['status'] in ['failed','cancelled']:
            raise RuntimeError(json.dumps(job,ensure_ascii=False))
        time.sleep(0.5)
    raise TimeoutError(identifier)

def post(path,payload):
    return client.post(path,json=payload).raise_for_status().json()

health=client.get('/api/health').raise_for_status().json()
assert '4060' in health['gpu']['name']
with (ROOT/'vendor/TripoSR/examples/robot.png').open('rb') as image:
    generated=ready(client.post('/api/jobs',files={'image':('robot.png',image,'image/png')},data={'options':json.dumps({'quality':'balanced','remove_background':True,'foreground_ratio':0.85,'crop':[0.02,0.02,0.98,0.98],'texture_resolution':512})}).raise_for_status().json())
assert generated['metadata']['triangles']>100
assert generated['metadata']['uv_meshes']==1
assert generated['metadata']['offline_network_blocked']
original=client.get(generated['artifacts']['original']).raise_for_status().content
original_hash=hashlib.sha256(original).hexdigest()
operations=[]
current=generated
for name in ['center','recalculate_normals','apply_transforms','fix_scale','triangulate','validate','inspect_materials']:
    current=ready(post('/api/jobs/'+current['id']+'/operations',{'operation':name,'height':1.5,'ratio':0.5}))
    assert current['metadata']['triangles']>0
    assert current['metadata']['uv_meshes']==1
    operations.append({'operation':name,'id':current['id'],'triangles':current['metadata']['triangles']})
assert abs(current['metadata']['dimensions'][2]-1.5)<0.001
exported=ready(post('/api/jobs/'+current['id']+'/export',{'pipeline':'URP'}))
validation=client.get(exported['artifacts']['validation']).raise_for_status().json()
assert validation['passed'] and validation['external_textures']
assert validation['before']['triangles']==validation['after']['triangles']
assert hashlib.sha256(client.get(generated['artifacts']['original']).content).hexdigest()==original_hash
zip_path=ROOT/'data/verified-Unity.zip'
zip_path.write_bytes(client.get(exported['artifacts']['unity_zip']).raise_for_status().content)
with zipfile.ZipFile(zip_path) as archive:
    assert archive.testzip() is None
    assert 'Forge3D_Asset/Models/Model.fbx' in archive.namelist()
    assert any(name.startswith('Forge3D_Asset/Textures/') for name in archive.namelist())
    manifest=json.loads(archive.read('Forge3D_Asset/asset_manifest.json'))
    assert manifest['editor_class'].endswith(exported['id'])
report={'passed':True,'generation':generated,'operations':operations,'export':exported,'fbx_validation':validation,'download_zip':str(zip_path),'zip_sha256':hashlib.sha256(zip_path.read_bytes()).hexdigest()}
(ROOT/'data/flow_verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({'passed':True,'generated':generated['id'],'export':exported['id'],'triangles':generated['metadata']['triangles'],'height_m':current['metadata']['dimensions'][2],'operations':len(operations),'offline':True},indent=2),flush=True)
