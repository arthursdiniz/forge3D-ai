"""User-authorized public resources; hashes/publisher/license provenance retained."""
import argparse
import hashlib
import json
import os
import time
import urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def fetch(url,path,expected_size=None,expected_sha=None):
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_name(path.name+'.part')
    digest=hashlib.sha256();count=0;started=time.monotonic();last=started
    with urllib.request.urlopen(url,timeout=120) as source,temporary.open('wb') as output:
        while chunk:=source.read(4*1024*1024):
            output.write(chunk);digest.update(chunk);count+=len(chunk)
            if time.monotonic()-last>=30:
                print(json.dumps({'file':path.name,'downloaded_bytes':count,'expected_bytes':expected_size,'seconds':round(time.monotonic()-started)}),flush=True);last=time.monotonic()
    sha=digest.hexdigest()
    if expected_size is not None and count!=expected_size:raise RuntimeError('Downloaded size mismatch.')
    if expected_sha is not None and sha!=expected_sha:raise RuntimeError('Downloaded SHA256 mismatch.')
    os.replace(temporary,path)
    return {'path':path.name,'bytes':count,'sha256':sha,'source':url}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('resource',choices=['pose','multiview']);args=parser.parse_args()
    if args.resource=='pose':
        root=ROOT/'models/character';files=[]
        files.append(fetch('https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/latest/pose_landmarker_lite.task',root/'pose_landmarker_lite.task',5777746))
        files.append(fetch('https://raw.githubusercontent.com/google-ai-edge/mediapipe/v0.10.32/LICENSE',root/'MEDIAPIPE_LICENSE.txt'))
        manifest={'download_complete':True,'publisher':'Google AI Edge','library_license':'Apache-2.0','model_name':'Pose Landmarker Lite','model_card':'https://storage.googleapis.com/mediapipe-assets/Model%20Card%20BlazePose%20GHUM%203D.pdf','usage':'local personal analysis; model license/card is distinct from code license','files':files}
    else:
        root=ROOT/'models/hunyuan-mv';revision='3a761b539b29fe4ff64714813aa9560fd66f5de0'
        base='https://huggingface.co/tencent/Hunyuan3D-2mv/resolve/'+revision+'/'
        files=[]
        for name,size,sha in [('hunyuan3d-dit-v2-mv/model.fp16.safetensors',4928151562,'d36f5881bcdc56726b73e517cd444c13c60732431622da7268145355c8d38e9c'),('hunyuan3d-dit-v2-mv/config.yaml',1608,None),('LICENSE',17828,None),('NOTICE',32064,None)]:
            item=fetch(base+name,root/name,size,sha);item['path']=name;files.append(item)
        manifest={'download_complete':True,'revision':revision,'code_revision':'f8db63096c8282cb27354314d896feba5ba6ff8a','publisher':'Tencent','library_license':'Tencent Hunyuan Community','authorization':'User major upgrade permits initial public model downloads, personal local use under previously disclosed Tencent terms; no gated credentials or paid service.','files':files}
    (root/'download_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print('PUBLIC_RESOURCE_DOWNLOAD_VERIFIED '+args.resource,flush=True)

if __name__=='__main__':main()
