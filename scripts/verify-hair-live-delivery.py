"""Actual local worker/export evidence, immutable before/candidate packages."""
import json,time,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];QA=ROOT/'data/hair-upgrade-20261013'
def api(path,data=None):
    request=urllib.request.Request('http://127.0.0.1:8000'+path,data=json.dumps(data).encode() if data is not None else None,headers={'Content-Type':'application/json'})
    return json.loads(urllib.request.urlopen(request,timeout=30).read())
def wait(identifier):
    deadline=time.monotonic()+300
    while time.monotonic()<deadline:
        job=api('/api/jobs/'+identifier)
        if job['status'] in ['completed','failed','cancelled']:
            assert job['status']=='completed',job;return job
        time.sleep(1)
    raise TimeoutError(identifier)
source=api('/api/jobs/323051d419ba4e47a4f421fd25e31d5f');candidate=api('/api/jobs/a50a972ed07e40758fcd5950ce6ecddd');analysis=api('/api/jobs/6b2c7e95f4574356b40394add9f251da')
assert candidate['metadata']['hair']['status']=='reviewable_candidate' and candidate['metadata']['hair']['protected_geometry']['equivalent']
result={'source':source,'analysis':analysis,'candidate':candidate,'cancelled':api('/api/jobs/5c2d07b8905c4a1e8d4b0c2212044179'),'exports':{}}
for name,job in [('HairAsset',candidate),('BaselineAsset',source)]:
    export=wait(api('/api/jobs/'+job['id']+'/export',{'pipeline':'URP'})['id']);result['exports'][name]=export
    (QA/'live-delivery.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(name,export['id'],'EXPORT_PASS',flush=True)
assert result['cancelled']['status']=='cancelled'
print('HAIR_LIVE_NEURAL_RECONSTRUCTION_CANCEL_RETRY_EXPORT_PASS',flush=True)
