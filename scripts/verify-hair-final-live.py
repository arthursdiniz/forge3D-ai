"""Repeat the actual local flow after the restored-crop regression fix."""
import json,time,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];QA=ROOT/'data/hair-upgrade-20261013'
def api(path,data=None,form=False):
    payload=urllib.parse.urlencode(data).encode() if form else json.dumps(data).encode() if data is not None else None
    request=urllib.request.Request('http://127.0.0.1:8000'+path,data=payload,headers={'Content-Type':'application/x-www-form-urlencoded' if form else 'application/json'})
    return json.loads(urllib.request.urlopen(request,timeout=30).read())
def wait(identifier):
    deadline=time.monotonic()+300
    while time.monotonic()<deadline:
        job=api('/api/jobs/'+identifier)
        if job['status'] in ['completed','failed','cancelled']:assert job['status']=='completed',job;return job
        time.sleep(1)
    raise TimeoutError(identifier)
result=json.loads((QA/'live-delivery.json').read_text());source=result['source'];settings={**result['analysis']['options'],'reference_analysis_id':result['analysis']['id'],'target_face':[.454,.10,.546,.18]}
analysis=wait(api('/api/jobs/'+source['id']+'/hair/analyze',{'options':json.dumps(settings)},True)['id']);result['analysis']=analysis
assert analysis['metadata']['hair_analysis']['before_silhouette']['candidate_pixels']==6339
print('RESTORED_CROP_NEURAL_MASK_PASS',analysis['id'],flush=True)
candidate=wait(api('/api/jobs/'+source['id']+'/hair/refine',{'analysis_id':analysis['id'],'front_axis':'negative_y','reviewed':True,'preset':'auto','attributes':{}})['id']);result['candidate']=candidate
assert candidate['metadata']['hair']['status']=='reviewable_candidate' and candidate['metadata']['hair']['protected_geometry']['equivalent'];print('FINAL_HAIR_GEOMETRY_PASS',candidate['id'],flush=True)
export=wait(api('/api/jobs/'+candidate['id']+'/export',{'pipeline':'URP'})['id']);result['exports']['HairAsset']=export
(QA/'live-delivery-final.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print('FINAL_HAIR_EXPORT_PASS',export['id'],flush=True)
