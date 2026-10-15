import hashlib,io,json,shutil
from pathlib import Path
from fastapi import APIRouter,File,Form,HTTPException,UploadFile
from PIL import Image,ImageOps
from pydantic import BaseModel,ConfigDict
from typing import Literal
from .contracts import HairAnalysisOptions,HairRefineOptions
from .resources import verify_resources,hair_status

class HairReview(BaseModel):
    model_config=ConfigDict(extra='forbid')
    decision:Literal['approve','reject']

def hair_reference(store,job):
    found=[];visited=set()
    while job:
        if job['id'] in visited:raise ValueError('Invalid ancestry.')
        visited.add(job['id']);folder=store.directory(job['id'])
        for relative in ['source.png','references/front/source.png']:
            path=folder/relative
            if path.is_file() and path.resolve().is_relative_to(store.root.resolve()):
                with Image.open(path) as image:
                    if image.width*image.height<=25_000_000:found.append((image.width*image.height,-len(visited),path))
        job=store.get(job['parent']) if job.get('parent') else None
    return max(found,key=lambda item:item[:2])[2] if found else None

def hair_router(root,store):
    root=Path(root);router=APIRouter()
    def source(identifier,visited=None):
        visited=set() if visited is None else visited
        if identifier in visited:raise HTTPException(409,'Invalid hair ancestry; choose the retained original.')
        visited.add(identifier)
        job=store.get(identifier)
        if not job:raise HTTPException(404,'Source not found.')
        if job['status']!='completed' or not (store.directory(identifier)/'model.glb').is_file():raise HTTPException(409,'Source mesh is not ready.')
        # Iterations always start from the retained original, never stack generated hair.
        if job['kind']=='hair' or 'hair' in job.get('metadata',{}):
            base=job.get('metadata',{}).get('hair',{}).get('base_source_asset')
            if not base:raise HTTPException(409,'Missing retained hair source.')
            return source(base,visited)
        return job
    @router.get('/api/hair/status')
    def status():return hair_status(root)
    @router.post('/api/jobs/{identifier}/hair/analyze',status_code=201)
    async def analyze(identifier:str,options:str=Form('{}'),reference:UploadFile|None=File(None),side:UploadFile|None=File(None),back:UploadFile|None=File(None)):
        job=source(identifier)
        try:settings=HairAnalysisOptions.model_validate_json(options)
        except ValueError as error:raise HTTPException(422,str(error))
        if not verify_resources(root)['ready']:raise HTTPException(409,'Optional local hair resources are unavailable; existing workflows remain available.')
        cached=None
        if settings.reference_analysis_id:
            prior=store.get(settings.reference_analysis_id)
            if not prior or prior['kind']!='hair_analysis' or prior['status']!='completed' or prior['parent']!=job['id']:raise HTTPException(409,'Cached reference does not belong to this source.')
            cached=store.directory(prior['id'])
        if reference:
            payload=await reference.read(20*1024*1024+1)
            if len(payload)>20*1024*1024:raise HTTPException(413,'Reference exceeds20MB.')
            try:
                image=Image.open(io.BytesIO(payload))
                if image.format not in ['PNG','JPEG','WEBP'] or min(image.size)<16 or image.width*image.height>25_000_000:raise ValueError('Invalid reference dimensions/format.')
                image=ImageOps.exif_transpose(image).convert('RGBA')
            except (ValueError,OSError,Image.DecompressionBombError) as error:raise HTTPException(422,str(error))
        else:
            path=cached/'source.png' if cached else hair_reference(store,job)
            if path is None:raise HTTPException(422,'Upload a reference showing the hair/head.')
            if not path.is_file() or not path.resolve().is_relative_to(store.root.resolve()):raise HTTPException(409,'Cached hair reference is unavailable.')
            with Image.open(path) as current:
                if current.width*current.height>25_000_000:raise HTTPException(422,'Cached reference dimensions exceed limit.')
                image=ImageOps.exif_transpose(current).convert('RGBA')
            payload=path.read_bytes()
        extras={}
        if cached:
            for name in ['side','back']:
                path=cached/f'reference_{name}.png'
                if path.is_file() and path.resolve().is_relative_to(store.root.resolve()):
                    with Image.open(path) as current:
                        if current.width*current.height>25_000_000:raise HTTPException(422,'Cached extra reference dimensions exceed limit.')
                        extras[name]=current.convert('RGBA')
        for name,upload in [('side',side),('back',back)]:
            if upload is None:continue
            raw=await upload.read(20*1024*1024+1)
            if len(raw)>20*1024*1024:raise HTTPException(413,'Extra hair reference exceeds20MB.')
            try:
                current=Image.open(io.BytesIO(raw))
                if current.format not in ['PNG','JPEG','WEBP'] or min(current.size)<16 or current.width*current.height>25_000_000:raise ValueError('Invalid extra reference dimensions/format.')
                extras[name]=ImageOps.exif_transpose(current).convert('RGBA')
            except (ValueError,OSError,Image.DecompressionBombError) as error:raise HTTPException(422,str(error))
        child=store.create(job['name']+' · Hair analysis',job['provider'],settings.model_dump(),kind='hair_analysis',parent=job['id'],initial_status='uploading');folder=store.directory(child['id']);image.save(folder/'source.png');(folder/'source_upload.bin').write_bytes(payload)
        for name,current in extras.items():current.save(folder/f'reference_{name}.png')
        return store.update(child['id'],status='queued')
    @router.post('/api/jobs/{identifier}/hair/refine',status_code=201)
    def refine(identifier:str,options:HairRefineOptions):
        job=source(identifier);analysis=store.get(options.analysis_id)
        if not analysis or analysis['kind']!='hair_analysis' or analysis['status']!='completed' or analysis['parent']!=job['id']:raise HTTPException(409,'Analysis does not belong to this completed source.')
        record=analysis.get('metadata',{}).get('hair_analysis',{});digest=hashlib.sha256((store.directory(job['id'])/'model.glb').read_bytes()).hexdigest()
        if record.get('status')!='reviewable':raise HTTPException(409,'Prepare a safe hair/head analysis before reconstruction.')
        if record.get('source_sha256')!=digest or record.get('front_axis')!=options.front_axis:raise HTTPException(409,'Source/camera changed; prepare and review hair again.')
        if not hair_status(root)['available']:raise HTTPException(409,'Hair reconstruction awaits actual local geometry/export proof.')
        return store.create(job['name']+' · Hair volume',job['provider'],options.model_dump(exclude_none=True),kind='hair',parent=job['id'])
    @router.post('/api/jobs/{identifier}/hair/review')
    def review(identifier:str,options:HairReview):
        job=store.get(identifier)
        if not job or job['kind']!='hair' or job['status']!='completed':raise HTTPException(409,'No completed hair candidate.')
        if options.decision=='approve' and job['metadata']['hair']['status']!='reviewable_candidate':raise HTTPException(409,'Inconclusive geometry retained previous model.')
        selected=job['id'] if options.decision=='approve' else job['parent'];folder=store.directory(identifier)
        from backend.config import atomic_json
        record={'decision':options.decision,'selected':selected,'original_retained':True};atomic_json(folder/'hair_review.json',record);return record
    return router
