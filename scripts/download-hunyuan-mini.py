"""User-authorized public FP16 shape weights only, pinned and hash checked."""
import hashlib
import io
import json
import zipfile
from pathlib import Path
import httpx

ROOT=Path(__file__).resolve().parents[1]
REV='f90a0f7df7d5e6f71109cf333f6a95a0ae3194a6'
CODE='f8db63096c8282cb27354314d896feba5ba6ff8a'

def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(8*1024*1024),b''):h.update(block)
    return h.hexdigest()

def main():
    weights=ROOT/'models/hunyuan-mini';weights.mkdir(parents=True,exist_ok=True)
    with httpx.Client(follow_redirects=True,timeout=httpx.Timeout(60,read=120)) as client:
        response=client.get(f'https://huggingface.co/api/models/tencent/Hunyuan3D-2mini/revision/{REV}',params={'blobs':'true'});response.raise_for_status();metadata=response.json()
        if metadata.get('gated'):raise RuntimeError('Stop: gated model is not authorized.')
        files=[]
        selected={'LICENSE','NOTICE','hunyuan3d-dit-v2-mini/config.yaml','hunyuan3d-dit-v2-mini/model.fp16.safetensors'}
        for entry in metadata['siblings']:
            if entry['rfilename'] not in selected:continue
            name=entry['rfilename'];path=weights/name;path.parent.mkdir(exist_ok=True,parents=True)
            expected=entry.get('lfs',{}).get('sha256')
            if not path.exists():
                part=path.with_suffix(path.suffix+'.part')
                if part.exists():raise RuntimeError(f'Partial download exists: {part}. Preserve and inspect it before retrying.')
                with client.stream('GET',f'https://huggingface.co/tencent/Hunyuan3D-2mini/resolve/{REV}/{name}?download=true') as response:
                    response.raise_for_status();received=0;next_notice=256*1024*1024
                    with part.open('wb') as stream:
                        for block in response.iter_bytes(8*1024*1024):
                            stream.write(block);received+=len(block)
                            if received>=next_notice:
                                print(json.dumps({'file':name,'received_bytes':received,'total_bytes':entry['size']}),flush=True);next_notice+=256*1024*1024
                if part.stat().st_size!=entry['size'] or (expected and digest(part)!=expected):raise RuntimeError('Downloaded file fails size/hash validation; retained .part.')
                part.replace(path)
            actual=digest(path)
            if path.stat().st_size!=entry['size'] or (expected and actual!=expected):raise RuntimeError('Existing weights fail validation.')
            files.append({'path':name,'bytes':path.stat().st_size,'sha256':actual,'publisher_sha256':expected})
        vendor=ROOT/'vendor/Hunyuan3D-2'
        if not vendor.exists():
            response=client.get(f'https://codeload.github.com/Tencent-Hunyuan/Hunyuan3D-2/zip/{CODE}');response.raise_for_status()
            archive=zipfile.ZipFile(io.BytesIO(response.content));vendor.mkdir()
            for info in archive.infolist():
                relative=Path(*Path(info.filename).parts[1:])
                if info.is_dir() or not (str(relative).replace('\\','/').startswith('hy3dgen/shapegen/') or relative.as_posix() in ['hy3dgen/__init__.py','LICENSE','NOTICE','requirements.txt','setup.py']):continue
                target=(vendor/relative).resolve()
                if not target.is_relative_to(vendor.resolve()):raise RuntimeError('Archive path escapes vendor directory.')
                target.parent.mkdir(exist_ok=True,parents=True);target.write_bytes(archive.read(info))
        manifest={'download_complete':True,'model':'tencent/Hunyuan3D-2mini','revision':REV,'code_revision':CODE,'files':files,'license':'Tencent Hunyuan Community; user explicitly authorized personal local trial in this chat2026-10-11','scope':'Standard mini FP16 shape only. No paint, turbo duplicates or external encoder downloads.'}
        (weights/'download_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
        print('PUBLIC_HUNYUAN_MINI_WEIGHTS_AND_CODE_VERIFIED',flush=True)

if __name__=='__main__':main()
