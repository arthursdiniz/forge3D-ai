"""Approved official TripoSG weights only; pinned revision, resume, SHA256."""
import hashlib
import json
import time
from pathlib import Path
import httpx

ROOT=Path(__file__).resolve().parents[1]
REPO='VAST-AI/TripoSG'
REVISION='2c1c516d22d58db486a058d98d31bb6177344e06'
FILES={'README.md','model_index.json','feature_extractor_dinov2/preprocessor_config.json','image_encoder_dinov2/config.json','image_encoder_dinov2/model.safetensors','scheduler/scheduler_config.json','transformer/config.json','transformer/diffusion_pytorch_model.safetensors','vae/config.json','vae/diffusion_pytorch_model.safetensors'}

def sha256(path):
    digest=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(8*1024*1024),b''):digest.update(chunk)
    return digest.hexdigest()

def main():
    directory=ROOT/'models/triposg';directory.mkdir(parents=True,exist_ok=True)
    with httpx.Client(follow_redirects=True,timeout=httpx.Timeout(120,connect=30)) as client:
        info=client.get(f'https://huggingface.co/api/models/{REPO}/revision/{REVISION}',params={'blobs':'true'}).raise_for_status().json()
        if info['sha']!=REVISION or info.get('cardData',{}).get('license')!='mit':raise RuntimeError('Official revision/license does not match reviewed source.')
        siblings={row['rfilename']:row for row in info['siblings']}
        if not FILES.issubset(siblings):raise RuntimeError('Expected official files missing.')
        total=sum(siblings[name]['size'] for name in FILES)
        if total>8*1024**3:raise RuntimeError('Download exceeds approved size; review required.')
        manifest={'repo':REPO,'revision':REVISION,'license':'MIT','approved_by_user':True,'total_bytes':total,'files':[]}
        (directory/'download_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
        for name in sorted(FILES):
            row=siblings[name];expected=row.get('lfs',{}).get('sha256')
            target=directory/name;target.parent.mkdir(parents=True,exist_ok=True)
            if target.exists() and target.stat().st_size==row['size'] and (not expected or sha256(target)==expected):
                print(json.dumps({'file':name,'status':'verified_cached'}),flush=True)
            else:
                part=target.with_name(target.name+'.partial')
                for attempt in range(5):
                    offset=part.stat().st_size if part.exists() else 0
                    if offset==row['size']:break
                    try:
                        headers={'Range':f'bytes={offset}-'} if offset else {}
                        # Avoid caching an expired signed redirect on retry/resume.
                        url=f'https://huggingface.co/{REPO}/resolve/{REVISION}/{name}?download=true&attempt={attempt}&offset={offset}'
                        with client.stream('GET',url,headers=headers) as response:
                            response.raise_for_status()
                            if offset and response.status_code!=206:offset=0
                            mode='ab' if offset else 'wb'
                            last=-1
                            with part.open(mode) as stream:
                                for chunk in response.iter_bytes(4*1024*1024):
                                    stream.write(chunk);offset+=len(chunk)
                                    progress=int(offset/max(row['size'],1)*100)
                                    if progress//5!=last:
                                        print(json.dumps({'file':name,'downloaded_bytes':offset,'total_bytes':row['size'],'percent':progress}),flush=True);last=progress//5
                        if part.stat().st_size==row['size']:break
                    except (httpx.HTTPError,OSError) as error:
                        print(json.dumps({'file':name,'retry':attempt+1,'error':str(error)}),flush=True)
                        if attempt==4:raise
                        time.sleep(2)
                if part.stat().st_size!=row['size']:raise RuntimeError('Incomplete download: '+name)
                actual=sha256(part)
                if expected and actual!=expected:raise RuntimeError('SHA256 mismatch: '+name+'; partial retained for diagnosis.')
                part.replace(target)
            manifest['files'].append({'path':name,'bytes':target.stat().st_size,'sha256':sha256(target),'publisher_sha256':expected})
            (directory/'download_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
        manifest['download_complete']=True
        (directory/'download_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
        print('TRIPOSG_OFFICIAL_WEIGHTS_VERIFIED',flush=True)
if __name__=='__main__':main()
