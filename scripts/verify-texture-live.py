"""Actual localhost cancel→retry neural run, immutable source and stage/VRAM evidence."""
import hashlib
import io
import json
import time
import urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BASE='http://127.0.0.1:8000'
def request(path,data=None,headers=None):
    req=urllib.request.Request(BASE+path,data=data,headers=headers or {})
    with urllib.request.urlopen(req,timeout=30) as response:return json.load(response)
def submit():
    boundary='ForgeTextureRealQA20261012';fields={'options':json.dumps({'provider':'neural_multiview','conditioning':'image','resolution':2048,'uv_mode':'preserve','front_axis':'negative_y','prompt':'anime volleyball player with orange hair, black and orange uniform, number 10','style':'anime','seed':44})}
    chunks=[]
    for key,value in fields.items():chunks.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode())
    chunks.append(f'--{boundary}\r\nContent-Disposition: form-data; name="front"; filename="hinata.png"\r\nContent-Type: image/png\r\n\r\n'.encode()+(ROOT/'data/test-inputs/hinata-shoyo-reference-20261011.png').read_bytes()+b'\r\n')
    chunks.append(f'--{boundary}--\r\n'.encode())
    return request('/api/jobs/d50d2f098559482ca796bb59672b7289/texture',b''.join(chunks),{'Content-Type':'multipart/form-data; boundary='+boundary})
source=ROOT/'data/assets/d50d2f098559482ca796bb59672b7289/model.glb';digest=hashlib.sha256(source.read_bytes()).hexdigest()
cancelled=submit()
for _ in range(30):
    job=request('/api/jobs/'+cancelled['id'])
    if job['status']=='generating':break
    time.sleep(1)
request('/api/jobs/'+cancelled['id']+'/cancel',b'')
retry=submit();stages=[];started=time.monotonic()
while time.monotonic()-started<600:
    job=request('/api/jobs/'+retry['id'])
    if not stages or stages[-1]!=job['stage']:stages.append(job['stage']);print(job['stage'],flush=True)
    if job['status'] in ['completed','failed','cancelled']:break
    time.sleep(2)
assert job['status']=='completed',job
assert request('/api/jobs/'+cancelled['id'])['status']=='cancelled'
assert hashlib.sha256(source.read_bytes()).hexdigest()==digest
assert job['metadata']['texture']['geometry']['equivalent']
report={'cancelled':cancelled['id'],'retry':retry['id'],'source_immutable':True,'stages':stages,'texture':job['metadata']['texture'],'timing':job['metadata']['timing']}
(ROOT/'data/texture-engine-20261012/live-flow.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('LIVE_CANCEL_RETRY_TEXTURE_PASS '+retry['id'],flush=True)
