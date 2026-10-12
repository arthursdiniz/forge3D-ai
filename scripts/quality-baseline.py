"""Preserve a real pre-upgrade API benchmark; never modifies existing assets."""
import hashlib
import json
import shutil
import time
from pathlib import Path
import httpx

ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/'data/quality-upgrade/baseline'
if DEST.exists():raise RuntimeError('Baseline preservado já existe. Não sobrescrever; use outro diretório para uma nova avaliação.')
DEST.mkdir(parents=True,exist_ok=False)
CASES=[('prop','teapot.png'),('stylized_character','robot.png'),('detailed_scene','chair.png')]
client=httpx.Client(base_url='http://127.0.0.1:8000',timeout=30)

def wait(record):
    limit=time.monotonic()+900
    while time.monotonic()<limit:
        record=client.get('/api/jobs/'+record['id']).raise_for_status().json()
        if record['status']=='completed':return record
        if record['status'] in ['failed','cancelled']:raise RuntimeError(record['error'])
        time.sleep(0.5)
    raise TimeoutError(record['id'])

results=[]
for category,filename in CASES:
    image_path=ROOT/'vendor/TripoSR/examples'/filename
    with image_path.open('rb') as image:
        generated=wait(client.post('/api/jobs',files={'image':(filename,image,'image/png')},data={'options':json.dumps({'quality':'balanced','remove_background':False,'foreground_ratio':0.85,'texture_resolution':1024})}).raise_for_status().json())
    exported=wait(client.post('/api/jobs/'+generated['id']+'/export',json={'pipeline':'URP'}).raise_for_status().json())
    case_dir=DEST/category
    case_dir.mkdir(exist_ok=True)
    if generated['metadata'].get('pipeline_version',1)!=1:raise RuntimeError('O app já usa pipeline v2. Não pode representar baseline anterior.')
    shutil.copytree(ROOT/'data/assets'/generated['id'],case_dir/'generation')
    shutil.copytree(ROOT/'data/assets'/exported['id'],case_dir/'export')
    shutil.copy2(image_path,case_dir/'reference.png')
    record={'category':category,'reference':filename,'reference_sha256':hashlib.sha256(image_path.read_bytes()).hexdigest(),'generation':generated,'export':exported,'seed':None,'seed_supported':False}
    (case_dir/'record.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
    results.append(record)
    print(json.dumps({'category':category,'id':generated['id'],'triangles':generated['metadata']['triangles'],'vram':generated['metadata']['peak_vram_mb'],'fbx':True}),flush=True)
    (DEST/'manifest.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
print('REAL_BASELINE_COMPLETE',flush=True)
