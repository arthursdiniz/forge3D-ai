import io
import json
import os
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image, ImageOps, UnidentifiedImageError
from pydantic import ValidationError
from .providers import get_provider, provider_statuses, blender_path, gpu_health
from .comparison import comparison_router
from .quality_settings import validate_provider_options
from .schemas import ExportOptions, GenerationOptions, Operation
from .storage import Store
from .worker import Worker
from .instance import InstanceLock

ROOT=Path(__file__).resolve().parents[1]
Image.MAX_IMAGE_PIXELS=25_000_000

def create_app(data_root=None,start_worker=True):
    store=Store(Path(data_root) if data_root else ROOT/'data')
    worker=Worker(ROOT,store)
    @asynccontextmanager
    async def lifespan(app):
        lock=None
        if start_worker:
            lock=InstanceLock(store.root/'server.lock')
            lock.acquire()
            worker.start()
        try:
            yield
        finally:
            if start_worker:
                worker.close()
                lock.release()
    app=FastAPI(title='Forge3D AI',lifespan=lifespan)
    app.state.store=store
    from .texture_engine.routes import texture_router
    app.include_router(texture_router(ROOT,store))
    from .texture_engine.region_routes import region_router
    app.include_router(region_router(ROOT,store))
    from .hair.routes import hair_router
    app.include_router(hair_router(ROOT,store))
    from .texture_engine.semantic_routes import semantic_router
    app.include_router(semantic_router(ROOT,store))
    app.include_router(comparison_router(store.root))
    from .character_routes import character_router
    app.include_router(character_router(ROOT,store.root))
    @app.middleware('http')
    async def local_only(request,call_next):
        host=request.headers.get('host','').split(':')[0]
        if host not in ['127.0.0.1','localhost','testserver']:
            from fastapi.responses import JSONResponse
            return JSONResponse({'detail':'Servidor exclusivo para uso local.'},status_code=403)
        origin=request.headers.get('origin')
        if origin and origin not in ['http://127.0.0.1:8000','http://localhost:8000','http://127.0.0.1:5173','http://localhost:5173']:
            from fastapi.responses import JSONResponse
            return JSONResponse({'detail':'Origem não autorizada.'},status_code=403)
        return await call_next(request)

    @app.get('/api/health')
    def health():
        return {'status':'ok','local_only':True,'gpu':gpu_health(),'providers':provider_statuses(ROOT),'blender':str(blender_path(ROOT) or ''),'data_directory':str(store.assets),'operations':['decimate','recalculate_normals','center','apply_transforms','fix_scale','triangulate','validate','inspect_materials','cleanup','refine_silhouette'],'active_job':worker.current}

    @app.get('/api/config')
    def configuration():
        from .config import load_config
        return {**load_config(ROOT),'resolved_blender':str(blender_path(ROOT) or ''),'gpu':gpu_health()}

    @app.put('/api/config/blender')
    def set_blender(payload:dict):
        from .config import configure_blender
        if set(payload)!={'path'} or not isinstance(payload['path'],str):raise HTTPException(422,'Informe somente path absoluto.')
        try:return configure_blender(ROOT,payload['path'])
        except ValueError as error:raise HTTPException(422,str(error))

    def require_job(identifier):
        job=store.get(identifier)
        if not job:
            raise HTTPException(404,'Asset não encontrado.')
        return job

    @app.get('/api/jobs')
    def list_jobs():
        return store.list()

    @app.get('/api/jobs/{identifier}')
    def get_job(identifier:str):
        return require_job(identifier)

    @app.get('/api/jobs/{identifier}/original')
    def original_job(identifier:str):
        job=require_job(identifier)
        visited=set()
        while job.get('parent') and job['kind']!='generate':
            if job['id'] in visited:
                raise HTTPException(409,'Histórico inconsistente.')
            visited.add(job['id'])
            job=require_job(job['parent'])
        return job

    async def enqueue_generation(image,options,provider,left=None,back=None,right=None,*,workflow=None):
        try:selected_provider=get_provider(provider,ROOT)
        except ValueError:raise HTTPException(400,'Provedor desconhecido.')
        if provider!='triposr' and not selected_provider.health_check()['available']:
            raise HTTPException(400,'Provedor não validado ou ambiente incompleto. Use TripoSR após Setup-Forge3D.')
        try:
            settings=GenerationOptions.model_validate_json(options)
            validate_provider_options(provider,settings)
            if provider in ['triposg','hunyuan_mini','hunyuan_mv'] and {'high':'quality','draft':'fast'}.get(settings.quality,settings.quality) not in selected_provider.health_check()['presets']:
                raise ValueError('Perfil ainda não validado neste hardware.')
            if settings.crop:
                crop_left,crop_top,crop_right,crop_bottom=settings.crop
                if not (0<=crop_left<crop_right<=1 and 0<=crop_top<crop_bottom<=1):
                    raise ValueError('Coordenadas de recorte inválidas.')
        except (ValidationError,ValueError) as error:
            raise HTTPException(422,str(error))
        content=await image.read(20*1024*1024+1)
        if len(content)>20*1024*1024:
            raise HTTPException(413,'Imagem excede 20 MB.')
        try:
            loaded=Image.open(io.BytesIO(content))
            if loaded.format not in ['PNG','JPEG','WEBP']:
                raise ValueError('Use PNG, JPG ou WEBP.')
            if loaded.width<16 or loaded.height<16 or loaded.width*loaded.height>25_000_000:
                raise ValueError('Dimensões inválidas: mínimo 16 px, máximo 25 megapixels.')
            loaded.load()
            converted=ImageOps.exif_transpose(loaded).convert('RGBA')
        except (UnidentifiedImageError,OSError,ValueError,Image.DecompressionBombError) as error:
            raise HTTPException(400,'Imagem inválida. '+str(error))
        references={'front':(content,converted)}
        for view,upload in [('left',left),('back',back),('right',right)]:
            if upload is None:continue
            extra=await upload.read(20*1024*1024+1)
            if len(extra)>20*1024*1024:raise HTTPException(413,'Cada vista deve ter até20MB.')
            try:
                picture=Image.open(io.BytesIO(extra))
                if picture.format not in ['PNG','JPEG','WEBP'] or min(picture.size)<16 or picture.width*picture.height>25_000_000:raise ValueError('Formato/dimensões inválidos.')
                picture.load();references[view]=(extra,ImageOps.exif_transpose(picture).convert('RGBA'))
            except (UnidentifiedImageError,OSError,ValueError,Image.DecompressionBombError) as error:raise HTTPException(400,f'Vista {view} inválida: '+str(error))
        if provider=='hunyuan_mv':
            from .hunyuan_mv_provider import validate_native_views
            try:
                validate_native_views(references)
                if len(references) not in selected_provider.health_check().get('validated_view_counts',[]):raise ValueError('Quantidade de vistas ainda não validada localmente para este perfil.')
            except ValueError as error:raise HTTPException(422,str(error))
        interpretation=None
        if settings.character_mode and not settings.analysis_id:raise HTTPException(422,'Revise e salve a interpretação do personagem antes de gerar.')
        if settings.character_mode and settings.analysis_id:
            file=store.root/'character-analyses'/settings.analysis_id/'analysis.json'
            try:interpretation=json.loads(file.read_text(encoding='utf-8'))
            except (OSError,ValueError):raise HTTPException(422,'Interpretação não encontrada; analise a referência novamente.')
            if not interpretation.get('reviewed'):raise HTTPException(422,'Revise e salve a interpretação antes de gerar.')
            import hashlib
            if interpretation.get('effective_image_sha256')!=hashlib.sha256(converted.tobytes()).hexdigest():raise HTTPException(422,'A interpretação pertence a outra referência; analise a imagem atual.')
            from .reference_coordinates import cropped_interpretation
            original_interpretation=interpretation
            try:interpretation=cropped_interpretation(interpretation,settings.crop)
            except ValueError as error:raise HTTPException(422,str(error))
        if settings.strategy=='base_mesh':
            if provider!='character_base_mesh':raise HTTPException(422,'Selecione o template próprio para a estratégia base_mesh; não substituir uma geração neural silenciosamente.')
            try:
                from .character_base_mesh import validate_reviewed_body
                validate_reviewed_body(interpretation)
            except (ValueError,KeyError) as error:raise HTTPException(422,str(error))
        if provider=='hunyuan_mini' and (settings.reference_texture=='front' or settings.refine_reference):
            masked=converted
            if settings.crop:
                crop_left,crop_top,crop_right,crop_bottom=settings.crop
                masked=converted.crop((round(crop_left*converted.width),round(crop_top*converted.height),round(crop_right*converted.width),round(crop_bottom*converted.height)))
            if settings.background_mode in ['keep','preserve_alpha'] and masked.getchannel('A').getextrema()[0]==255:
                raise HTTPException(422,'Projeção/refinamento exige máscara do objeto. Use fundo automático/remoção ou uma imagem com alpha.')
        job=store.create(Path(image.filename or 'Asset').stem,provider,settings.model_dump(),kind='model_workflow' if workflow else 'generate',initial_status='uploading')
        directory=store.directory(job['id'])
        (directory/'source_upload.bin').write_bytes(content)
        converted.save(directory/'source.png')
        import hashlib
        bundle={'conditioning':'native_multiview' if provider=='hunyuan_mv' else 'front_only; extra views reserved for diagnosis/projection','views':{}}
        for view,(payload,picture) in references.items():
            target=directory/'references'/view;target.mkdir(parents=True)
            (target/'source_upload.bin').write_bytes(payload);picture.save(target/'source.png')
            bundle['views'][view]={'path':str((target/'source.png').resolve()),'sha256':hashlib.sha256(payload).hexdigest(),'size':list(picture.size)}
        from .config import atomic_json
        atomic_json(directory/'references.json',bundle)
        if interpretation:
            from .config import atomic_json
            atomic_json(directory/'character_interpretation_original.json',original_interpretation)
            atomic_json(directory/'character_interpretation.json',interpretation)
        metadata={}
        if workflow:
            atomic_json(directory/'workflow.json',workflow)
            metadata['workflow']=workflow
        return store.update(job['id'],status='queued',metadata=metadata)

    @app.post('/api/jobs',status_code=201)
    async def generate(image:UploadFile=File(...),options:str=Form('{}'),provider:str=Form('triposr'),left:UploadFile|None=File(None),back:UploadFile|None=File(None),right:UploadFile|None=File(None)):
        return await enqueue_generation(image,options,provider,left,back,right)

    from .workflows.routes import workflow_router
    app.include_router(workflow_router(ROOT,store,enqueue_generation))

    @app.post('/api/jobs/{identifier}/cancel')
    def cancel(identifier:str):
        require_job(identifier)
        try:
            return store.cancel(identifier)
        except ValueError as error:
            raise HTTPException(409,str(error))

    @app.post('/api/jobs/{identifier}/operations',status_code=201)
    def operate(identifier:str,options:Operation):
        job=require_job(identifier)
        if job['status']!='completed' or 'model' not in job['artifacts']:
            raise HTTPException(409,'Aguarde o modelo ficar pronto.')
        if options.operation=='sculpt_refine' and options.region_bounds is None:raise HTTPException(422,'Selecione região local antes do refinamento micro.')
        if options.operation=='symmetry' and options.symmetry_mode!='off':
            origin=job;visited=set()
            while origin.get('parent') and origin['kind']!='generate':
                if origin['id'] in visited:raise HTTPException(409,'Histórico inconsistente.')
                visited.add(origin['id']);origin=require_job(origin['parent'])
            try:interpretation=json.loads((store.directory(origin['id'])/'character_interpretation.json').read_text(encoding='utf-8'))
            except (OSError,ValueError):raise HTTPException(422,'Simetria exige interpretação revisada do personagem.')
            if interpretation.get('pose') not in ['neutral','a_pose','t_pose'] or interpretation.get('view')!='front':raise HTTPException(422,'Pose dinâmica/desconhecida não deve ser forçada à simetria; revise pose frontal/plano.')
            if options.region_bounds is None and not any(interpretation.get('regions',{}).get(name,{}).get('bounds') for name in options.symmetry_regions):raise HTTPException(422,'Regiões selecionadas não têm limites revisados.')
        if options.operation=='refine_silhouette' and job['provider'] not in ['triposg','hunyuan_mini']:
            raise HTTPException(422,'Refinamento frontal validado somente para TripoSG/Hunyuan-mini.')
        if options.operation=='refine_silhouette' and (job.get('metadata') or {}).get('image_preparation',{}).get('background_action')=='kept':
            raise HTTPException(422,'Refinamento exige máscara do objeto. Gere com remoção de fundo ou alpha existente.')
        return store.create(job['name']+' · '+options.operation,job['provider'],options.model_dump(),kind='transform',parent=identifier)

    @app.post('/api/jobs/{identifier}/export',status_code=201)
    def export(identifier:str,options:ExportOptions):
        job=require_job(identifier)
        if job['status']!='completed' or 'model' not in job['artifacts']:
            raise HTTPException(409,'Aguarde o modelo ficar pronto.')
        return store.create(job['name']+' · Unity',job['provider'],options.model_dump(),kind='export',parent=identifier)

    @app.get('/api/files/{identifier}/{filename:path}')
    def file(identifier:str,filename:str):
        require_job(identifier)
        try:
            directory=store.directory(identifier).resolve()
            path=(directory/filename).resolve()
            if not path.is_relative_to(directory) or not path.is_file():
                raise ValueError('Arquivo indisponível')
            if path.suffix.lower() not in ['.glb','.fbx','.obj','.mtl','.zip','.png','.json','.md']:
                raise ValueError('Formato indisponível')
        except ValueError:
            raise HTTPException(404,'Arquivo não encontrado.')
        return FileResponse(path,filename=path.name if path.suffix in ['.zip','.fbx'] else None)

    dist=ROOT/'frontend/dist'
    if dist.exists():
        app.mount('/',StaticFiles(directory=dist,html=True),name='frontend')
    return app

app=create_app()
