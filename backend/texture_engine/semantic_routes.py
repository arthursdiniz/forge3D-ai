import hashlib,json,shutil
from pathlib import Path
from fastapi import APIRouter,Form,File,UploadFile,HTTPException
from PIL import Image
from .semantic_contracts import SemanticAnalysisOptions,SemanticPaintOptions
from .semantic_resources import semantic_status
from .semantic_taxonomy import CLASS_NAMES
from .region_routes import read_reference,ReviewChoice
from .face_reference import best_reference,character_context

def semantic_router(root,store):
    router=APIRouter();root=Path(root)
    def source(identifier):
        job=store.get(identifier)
        if not job or job['status']!='completed' or 'model' not in job['artifacts'] or not (store.directory(identifier)/'model.glb').is_file():raise HTTPException(409,'Choose a completed saved mesh.')
        return job
    def bound(identifier,analysis_id,axis=None):
        job=source(identifier);analysis=store.get(analysis_id)
        if not analysis or analysis['kind']!='semantic_analysis' or analysis['status']!='completed' or analysis['parent']!=identifier:raise HTTPException(409,'Semantic analysis belongs to another source or is incomplete.')
        report=analysis['metadata'].get('semantic_analysis',{});digest=hashlib.sha256((store.directory(identifier)/'model.glb').read_bytes()).hexdigest()
        if report.get('source_sha256')!=digest or (axis and report.get('front_axis')!=axis):raise HTTPException(409,'Source or camera changed; analyze and review again.')
        for name,view in report.get('views',{}).items():
            for relative,expected in view.get('file_sha256',{}).items():
                path=(store.directory(analysis_id)/'views'/name/relative).resolve()
                if not path.is_relative_to(store.directory(analysis_id).resolve()) or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=expected:raise HTTPException(409,'Saved semantic reference/mask changed; analyze and review again.')
        return job,analysis,report
    @router.get('/api/semantic/status')
    def status():return {**semantic_status(root),'classes':CLASS_NAMES}
    @router.post('/api/jobs/{identifier}/semantic/analyze',status_code=201)
    async def analyze(identifier:str,options:str=Form('{}'),front:UploadFile|None=File(None),back:UploadFile|None=File(None),left:UploadFile|None=File(None),right:UploadFile|None=File(None)):
        job=source(identifier)
        try:settings=SemanticAnalysisOptions.model_validate_json(options)
        except ValueError as error:raise HTTPException(422,str(error))
        if not semantic_status(root)['installed'] and any(v.profile!='manual' for v in settings.views.values()):raise HTTPException(409,'Local semantic parser unavailable; select explicit manual profile.')
        previous=None
        if settings.base_analysis_id:_,previous,_=bound(identifier,settings.base_analysis_id,settings.front_axis)
        images={};uploads={'front':front,'back':back,'left':left,'right':right}
        for name in settings.views:
            if uploads[name]:image,_=await read_reference(uploads[name])
            elif previous:
                path=store.directory(previous['id'])/'views'/name/'source.png'
                if not path.is_file():raise HTTPException(409,'This real reference view is absent from the saved analysis.')
                with Image.open(path) as current:image=current.convert('RGBA')
            elif name=='front':
                saved=best_reference(store,job)
                if not saved:raise HTTPException(422,'Upload a real front reference.')
                with Image.open(store.directory(saved['asset'])/saved['relative']) as current:image=current.convert('RGBA')
            else:raise HTTPException(422,'Upload each added real side/back reference; synthesized views are not observed truth.')
            images[name]=image
        child=store.create(job['name']+' · Semantic masks',job['provider'],settings.model_dump(),kind='semantic_analysis',parent=identifier,initial_status='uploading');folder=store.directory(child['id'])
        for name,image in images.items():path=folder/'views'/name;path.mkdir(parents=True);image.save(path/'source.png')
        suggestions={name:character_context(store,job,hashlib.sha256(image.tobytes()).hexdigest(),image) for name,image in images.items()}
        (folder/'character_context.json').write_text(json.dumps({'views':suggestions,'scope':'Suggestions from matching original image only; landmarks are not semantic masks.'}),encoding='utf-8')
        return store.update(child['id'],status='queued')
    @router.post('/api/jobs/{identifier}/semantic/paint',status_code=201)
    def paint(identifier:str,options:SemanticPaintOptions):
        job,analysis,report=bound(identifier,options.analysis_id,options.front_axis)
        if report.get('status')!='reviewable' or not report.get('views'):raise HTTPException(409,'Prepare valid source/target semantics before painting.')
        if not semantic_status(root)['available']:raise HTTPException(409,'Semantic editing awaits actual local projection/geometry/export validation.')
        return store.create(job['name']+' · Reference Fidelity',job['provider'],options.model_dump(),kind='texture',parent=identifier)
    @router.get('/api/jobs/{analysis_id}/semantic/surface')
    def surface(analysis_id:str,node:str,u:float,v:float):
        import math
        analysis=store.get(analysis_id)
        if not analysis or not analysis.get('parent'):raise HTTPException(404,'Analysis missing.')
        _,_,report=bound(analysis['parent'],analysis_id)
        if not all(math.isfinite(q) and 0<=q<=1 for q in [u,v]):raise HTTPException(422,'Invalid surface UV.')
        record=next((r for r in report.get('atlas',[]) if r['node']==node or r['geometry']==node),None)
        if not record:return {'class':'unknown','label':0,'origin':'unmapped surface'}
        folder=store.directory(analysis_id)
        with Image.open(folder/record['labels']) as image:label=int(image.getpixel((min(image.width-1,int(u*image.width)),min(image.height-1,int((1-v)*image.height)))))
        with Image.open(folder/record['origin']) as image:origin=int(image.getpixel((min(image.width-1,int(u*image.width)),min(image.height-1,int((1-v)*image.height)))))
        return {'class':CLASS_NAMES[label],'label':label,'origin':{0:'unknown or target estimate only',1:'observed projection with learned mask',2:'observed projection with manual mask'}[origin]}
    @router.post('/api/jobs/{identifier}/semantic/review')
    def review(identifier:str,choice:ReviewChoice):
        job=source(identifier)
        if job['kind']!='texture' or job['options'].get('provider')!='semantic_reference':raise HTTPException(409,'No completed semantic candidate.')
        report=job['metadata'].get('texture',{}).get('semantic',{})
        if choice.decision=='approve' and (report.get('status')!='reviewable_candidate' or not report.get('protected_pixels_equal')):raise HTTPException(409,'No protected, changed semantic candidate to approve.')
        record={'decision':choice.decision,'selected':identifier if choice.decision=='approve' else job['parent'],'original_retained':True};from backend.config import atomic_json
        atomic_json(store.directory(identifier)/'semantic_review.json',record);return record
    return router
