"""Actual localized cancel/retry/export flow after corrected global normals."""
import hashlib
import json
import time
import urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];qa=ROOT/'data/texture-fidelity-20261013';BASE='http://127.0.0.1:8000'
def request(path,data=None,headers=None):
    with urllib.request.urlopen(urllib.request.Request(BASE+path,data=data,headers=headers or {}),timeout=60) as response:return json.load(response)
parent=json.loads((qa/'registered-global-job.json').read_text());options=json.loads((qa/'hinata-regional-trial6-fidelity-angle/options.json').read_text());source=ROOT/'data/assets'/parent['id']/'model.glb';digest=hashlib.sha256(source.read_bytes()).hexdigest()
def submit():
    boundary='FidelityRegionLive';body=f'--{boundary}\r\nContent-Disposition: form-data; name="options"\r\n\r\n{json.dumps(options)}\r\n--{boundary}--\r\n'.encode()
    return request('/api/jobs/'+parent['id']+'/texture/refine',body,{'Content-Type':'multipart/form-data; boundary='+boundary})
cancelled=submit()
for _ in range(30):
    job=request('/api/jobs/'+cancelled['id'])
    if job['status']=='generating':break
    time.sleep(.5)
request('/api/jobs/'+cancelled['id']+'/cancel',b'');retry=submit();last=None;started=time.monotonic()
while time.monotonic()-started<300:
    job=request('/api/jobs/'+retry['id'])
    if job['stage']!=last:print(job['stage'],flush=True);last=job['stage']
    if job['status'] in ['completed','failed','cancelled']:break
    time.sleep(1)
assert job['status']=='completed',job
assert request('/api/jobs/'+cancelled['id'])['status']=='cancelled'
assert hashlib.sha256(source.read_bytes()).hexdigest()==digest
assert job['metadata']['texture']['regional']['outside_unchanged'] and job['metadata']['texture']['geometry']['equivalent']
(qa/'final-live-region-job.json').write_text(json.dumps(job,indent=2),encoding='utf-8')
export=request('/api/jobs/'+job['id']+'/export',b'{"pipeline":"URP"}',{'Content-Type':'application/json'})
for _ in range(180):
    export=request('/api/jobs/'+export['id'])
    if export['status'] in ['completed','failed','cancelled']:break
    time.sleep(1)
assert export['status']=='completed',export
folder=ROOT/'data/assets'/export['id']/'Forge3D_Asset';assert (folder/'SDXL_LICENSE.md').is_file() and (folder/'MV_ADAPTER_LICENSE.txt').is_file()
report={'source':parent['id'],'cancelled':cancelled['id'],'retry':job['id'],'export':export['id'],'package':str(folder),'source_immutable':True,'outside_unchanged':True,'metrics':job['metadata']['texture']['regional']['metrics'],'whole_job_seconds':job['metadata']['total_seconds']}
(qa/'final-live-flow.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print('LIVE_REGION_CANCEL_RETRY_EXPORT_PASS '+job['id']+' '+export['id'],flush=True)
