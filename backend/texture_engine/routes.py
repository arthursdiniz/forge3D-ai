import io
import json
import shutil
from pathlib import Path
from fastapi import APIRouter,File,Form,HTTPException,UploadFile
from PIL import Image,ImageOps
from .contracts import TextureOptions
from .providers import provider_statuses
from .import_safety import safe_name,validate_resources

def texture_router(root,store):
    router=APIRouter()
    @router.get('/api/texture/providers')
    def providers():return provider_statuses(root)

    @router.post('/api/models/import',status_code=201)
    async def import_model(model:UploadFile=File(...),sidecars:list[UploadFile]=File(default=[])):
        payload=await model.read(80*1024*1024+1)
        if len(payload)>80*1024*1024:raise HTTPException(413,'Model exceeds 80 MB.')
        if len(sidecars)>64:raise HTTPException(413,'Too many sidecars.')
        resources={};total=len(payload)
        try:
            name=safe_name(model.filename or '')
            for upload in sidecars:
                key=safe_name(upload.filename or '')
                if key.casefold() in {name.casefold(),*(item.casefold() for item in resources)}:raise ValueError('Duplicate filename.')
                body=await upload.read(40*1024*1024+1);total+=len(body)
                if len(body)>40*1024*1024 or total>150*1024*1024:raise HTTPException(413,'Sidecars exceed resource limits.')
                resources[key]=body
            extension=validate_resources(name,payload,resources)
        except (ValueError,UnicodeError,TypeError,AttributeError,KeyError) as error:raise HTTPException(422,str(error))
        job=store.create(Path(name).stem,'imported',{'filename':name,'format':extension},kind='import',initial_status='uploading')
        directory=store.directory(job['id'])/'uploads';directory.mkdir()
        (directory/name).write_bytes(payload)
        for key,body in resources.items():(directory/key).write_bytes(body)
        return store.update(job['id'],status='queued')

    @router.post('/api/jobs/{identifier}/texture',status_code=201)
    async def texture(identifier:str,options:str=Form('{}'),front:UploadFile|None=File(None),left:UploadFile|None=File(None),back:UploadFile|None=File(None),right:UploadFile|None=File(None)):
        parent=store.get(identifier)
        if not parent:raise HTTPException(404,'Source model not found.')
        if parent['status']!='completed' or not (store.directory(identifier)/'model.glb').is_file():raise HTTPException(409,'Source model is not ready.')
        try:settings=TextureOptions.model_validate_json(options)
        except ValueError as error:raise HTTPException(422,str(error))
        health=next(item for item in provider_statuses(root) if item['id']==settings.provider)
        if not health['available']:raise HTTPException(409,health['notes'])
        references={}
        for view,upload in [('front',front),('left',left),('back',back),('right',right)]:
            if upload is None:continue
            if view not in health['capabilities']['named_views']:raise HTTPException(422,'Provider does not condition on extra named views.')
            payload=await upload.read(20*1024*1024+1)
            if len(payload)>20*1024*1024:raise HTTPException(413,'Reference exceeds 20 MB.')
            try:
                image=Image.open(io.BytesIO(payload))
                if image.format not in ['PNG','JPEG','WEBP'] or min(image.size)<16 or image.width*image.height>25_000_000:raise ValueError('Invalid reference dimensions/format.')
                image.load();image=ImageOps.exif_transpose(image).convert('RGBA')
                if settings.background_mode=='preserve_alpha' and image.getchannel('A').getextrema()[0]==255:raise ValueError('A real alpha mask is required; select background removal for opaque inputs.')
                references[view]=(payload,image)
            except (OSError,ValueError,Image.DecompressionBombError) as error:raise HTTPException(422,str(error))
        saved={}
        if settings.use_saved_references:
            ancestor=parent;visited=set()
            while ancestor.get('parent'):
                if ancestor['id'] in visited:raise HTTPException(409,'Invalid ancestry.')
                visited.add(ancestor['id']);ancestor=store.get(ancestor['parent'])
                if not ancestor:raise HTTPException(409,'Missing ancestry.')
            source_dir=store.directory(ancestor['id'])
            for view in health['capabilities']['named_views']:
                paths=([source_dir/'prepared_masked.png'] if view=='front' else [])+[source_dir/'references'/view/'source.png']
                for path in paths:
                    if path.is_file() and path.resolve().is_relative_to(store.root) and view not in references:saved[view]=path;break
        if settings.conditioning=='image' and 'front' not in references and 'front' not in saved:raise HTTPException(422,'Upload a front reference or use a saved source reference.')
        if settings.conditioning=='text' and (references or saved):raise HTTPException(422,'Text-only conditioning does not consume image references.')
        job=store.create(parent['name']+' · Texture',parent['provider'],settings.model_dump(),kind='texture',parent=identifier,initial_status='uploading')
        directory=store.directory(job['id']);bundle={}
        for view,(payload,image) in references.items():
            target=directory/'references'/view;target.mkdir(parents=True);(target/'source_upload.bin').write_bytes(payload);image.save(target/'source.png');bundle[view]={'path':f'references/{view}/source.png'}
        for view,path in saved.items():
            target=directory/'references'/view;target.mkdir(parents=True);shutil.copy2(path,target/'source.png');bundle[view]={'path':f'references/{view}/source.png','copied_from_asset':ancestor['id']}
        (directory/'texture_references.json').write_text(json.dumps({'views':bundle},indent=2),encoding='utf-8')
        return store.update(job['id'],status='queued')
    return router
