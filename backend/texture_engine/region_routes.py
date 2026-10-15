"""Safe regional preparation/refinement and immutable review choices."""
import asyncio
import hashlib
import io
import json
import shutil
import uuid
from pathlib import Path
from fastapi import APIRouter,File,Form,HTTPException,UploadFile
from fastapi.responses import FileResponse
from PIL import Image,ImageOps
from pydantic import BaseModel,ConfigDict
from typing import Literal
from .contracts import RegionRefineOptions
from .face_reference import best_reference,character_context

def regional_ready(root):
    from .providers import regional_proof_valid,runtime_valid
    return runtime_valid(Path(root),'core') and regional_proof_valid(Path(root))

async def read_reference(upload):
    payload=await upload.read(20*1024*1024+1)
    if len(payload)>20*1024*1024:raise HTTPException(413,'Reference exceeds20MB.')
    try:
        image=Image.open(io.BytesIO(payload))
        if image.format not in ['PNG','JPEG','WEBP'] or image.width*image.height>25_000_000 or min(image.size)<16:raise ValueError('Invalid reference dimensions/format.')
        image.load();return ImageOps.exif_transpose(image).convert('RGBA'),payload
    except (OSError,ValueError,Image.DecompressionBombError) as error:raise HTTPException(422,str(error))

async def prepare_context(root,directory,axis,style):
    python=Path(root)/('.venv-texture' if (Path(root)/'.venv-texture/Scripts/python.exe').is_file() else '.venv-ai')/'Scripts/python.exe'
    import os
    env=os.environ.copy();env.pop('PYTHONPATH',None);env['PYTHONUTF8']='1'
    process=await asyncio.create_subprocess_exec(str(python),str(Path(root)/'backend/texture_engine/region_context.py'),'--directory',str(directory),'--axis',axis,'--style',style,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.STDOUT,cwd=str(root),env=env,creationflags=getattr(__import__('subprocess'),'CREATE_NO_WINDOW',0))
    try:output,_=await asyncio.wait_for(process.communicate(),60)
    except BaseException:
        if process.returncode is None:process.kill();await process.communicate()
        raise
    (directory/'context.log').write_bytes(output)
    if process.returncode:raise RuntimeError(output.decode('utf-8',errors='replace')[-2000:])
    return json.loads((directory/'context.json').read_text())

class ReviewChoice(BaseModel):
    model_config=ConfigDict(extra='forbid')
    decision:Literal['approve','reject']

def region_router(root,store):
    root=Path(root);router=APIRouter();base=store.root/'texture-regions'
    def parent(identifier):
        job=store.get(identifier)
        if not job:raise HTTPException(404,'Source model not found.')
        if job['status']!='completed' or not (store.directory(identifier)/'model.glb').is_file():raise HTTPException(409,'Source model is not ready.')
        return job
    async def obtain(job,upload):
        if upload:return (*await read_reference(upload),None)
        info=best_reference(store,job)
        if not info:raise HTTPException(422,'No original reference available; upload an optional face reference.')
        path=store.directory(info['asset'])/info['relative']
        with Image.open(path) as image:result=ImageOps.exif_transpose(image).convert('RGBA')
        return result,path.read_bytes(),info
    @router.get('/api/texture/regions/{identifier}/files/{filename}')
    def file(identifier:str,filename:str):
        if len(identifier)!=32 or any(c not in '0123456789abcdef' for c in identifier) or filename not in ['source.png','model_front.png','context.json']:raise HTTPException(404,'Regional preview not found.')
        path=base/identifier/filename
        if not path.is_file():raise HTTPException(404,'Regional preview not found.')
        return FileResponse(path)
    @router.post('/api/jobs/{identifier}/texture/context')
    async def context(identifier:str,reference:UploadFile|None=File(None),front_axis:Literal['negative_y','x']=Form('negative_y'),style:Literal['anime','stylized','realistic','object']=Form('anime')):
        job=parent(identifier);image,payload,info=await obtain(job,reference);context_id=uuid.uuid4().hex;directory=base/context_id;directory.mkdir(parents=True)
        image.save(directory/'source.png');shutil.copy2(store.directory(identifier)/'model.glb',directory/'model.glb')
        try:report=await prepare_context(root,directory,front_axis,style)
        except (RuntimeError,asyncio.TimeoutError) as error:raise HTTPException(422,str(error))
        report.update(id=context_id,source_job=identifier,source_sha256=hashlib.sha256((directory/'model.glb').read_bytes()).hexdigest(),reference_original=info,reference_sha256=hashlib.sha256(payload).hexdigest(),reference_url=f'/api/texture/regions/{context_id}/files/source.png',model_url=f'/api/texture/regions/{context_id}/files/model_front.png')
        report['character_intelligence']=character_context(store,job,report['reference_sha256'],image)
        report['cached_views_present']=(store.directory(identifier)/'neural.json').is_file()
        (directory/'context.json').write_text(json.dumps(report,indent=2),encoding='utf-8');return report
    @router.post('/api/jobs/{identifier}/texture/refine',status_code=201)
    async def refine(identifier:str,options:str=Form(...),reference:UploadFile|None=File(None)):
        job=parent(identifier)
        try:settings=RegionRefineOptions.model_validate_json(options)
        except ValueError as error:raise HTTPException(422,str(error))
        if not regional_ready(root):raise HTTPException(409,'Regional projection has not been validated locally.')
        image,payload,info=await obtain(job,reference)
        child=store.create(job['name']+' · '+settings.region+' reference',job['provider'],settings.model_dump(),kind='texture',parent=identifier,initial_status='uploading');directory=store.directory(child['id']);folder=directory/'references/front';folder.mkdir(parents=True);image.save(folder/'source.png');(folder/'source_upload.bin').write_bytes(payload)
        (directory/'texture_references.json').write_text(json.dumps({'views':{'front':{'path':'references/front/source.png','original':info,'explicit_regional_upload':reference is not None}}}),encoding='utf-8')
        return store.update(child['id'],status='queued')
    @router.post('/api/jobs/{identifier}/texture/review')
    def review(identifier:str,choice:ReviewChoice):
        job=parent(identifier)
        if job['kind']!='texture' or job['options'].get('provider')!='reference_region':raise HTTPException(409,'Only a completed regional candidate can be reviewed.')
        regional=job['metadata'].get('texture',{}).get('regional',{})
        if choice.decision=='approve' and regional.get('status')!='improved_candidate':raise HTTPException(409,'No measured improvement; previous version was retained.')
        review_id=uuid.uuid4().hex;directory=store.directory(identifier)/'reviews';directory.mkdir(exist_ok=True);record={'decision':choice.decision,'candidate':identifier,'previous':job['parent'],'selected':identifier if choice.decision=='approve' else job['parent']}
        (directory/(review_id+'.json')).write_text(json.dumps(record,indent=2),encoding='utf-8');return record
    return router
