"""Fresh final neural image job and export after the single review fix pass."""
import hashlib
import json
import time
import urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];qa=ROOT/'data/texture-engine-20261012';BASE='http://127.0.0.1:8000'
def request(path,data=None,headers=None):
    with urllib.request.urlopen(urllib.request.Request(BASE+path,data=data,headers=headers or {}),timeout=30) as response:return json.load(response)
def wait(identifier):
    started=time.monotonic();last=None
    while time.monotonic()-started<600:
        job=request('/api/jobs/'+identifier)
        if job['stage']!=last:print(job['stage'],flush=True);last=job['stage']
        if job['status'] in ['completed','failed','cancelled']:
            assert job['status']=='completed',job
            return job
        time.sleep(2)
    raise TimeoutError('Final QA job exceeded 600 seconds.')
source=ROOT/'data/assets/d50d2f098559482ca796bb59672b7289/model.glb';digest=hashlib.sha256(source.read_bytes()).hexdigest()
boundary='ForgeFinalTextureQA';options={'provider':'neural_multiview','conditioning':'image','resolution':4096,'uv_mode':'preserve','front_axis':'negative_y','prompt':'anime volleyball player with orange hair, black and orange uniform, number 10','style':'anime','seed':44}
payload=(f'--{boundary}\r\nContent-Disposition: form-data; name="options"\r\n\r\n{json.dumps(options)}\r\n--{boundary}\r\nContent-Disposition: form-data; name="front"; filename="hinata.png"\r\nContent-Type: image/png\r\n\r\n'.encode()+(ROOT/'data/test-inputs/hinata-shoyo-reference-20261011.png').read_bytes()+f'\r\n--{boundary}--\r\n'.encode())
job=request('/api/jobs/d50d2f098559482ca796bb59672b7289/texture',payload,{'Content-Type':'multipart/form-data; boundary='+boundary})
(qa/'delivery-texture-submission.json').write_text(json.dumps(job,indent=2),encoding='utf-8')
job=wait(job['id']);texture=job['metadata']['texture'];neural=texture['neural']
assert texture['geometry']['equivalent'] and neural['offline'] and neural['joint_views']==6
assert job['metadata']['peak_vram_mb']==neural['peak_allocated_mb'] and job['metadata']['inference_seconds']==neural['inference_seconds']
assert hashlib.sha256(source.read_bytes()).hexdigest()==digest
(qa/'delivery-texture-result.json').write_text(json.dumps(job,indent=2),encoding='utf-8')
export=wait(request('/api/jobs/'+job['id']+'/export',b'{"pipeline":"URP"}',{'Content-Type':'application/json'})['id'])
folder=ROOT/'data/assets'/export['id']/'Forge3D_Asset'
maps=[]
for line in (folder/'Models/Model.mtl').read_text().splitlines():
    if line.lstrip().startswith('map_'):
        uri=line.split()[-1];path=(folder/'Models'/uri).resolve()
        assert path.is_relative_to(folder.resolve()) and path.is_file(),uri
        maps.append(uri)
report={'texture':job['id'],'export':export['id'],'package':str(folder),'source_immutable':True,'obj_texture_paths':maps,'texture_metrics':neural,'whole_job_seconds':job['metadata']['total_seconds'],'world_export':json.loads((folder/'geometry_export_validation.json').read_text())}
(qa/'delivery-hinata-result.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('FINAL_NEURAL_TEXTURE_EXPORT_PASS '+job['id']+' '+export['id'],flush=True)
