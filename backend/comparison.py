"""Read actual benchmark artifacts and record manual ratings only."""
import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from .schemas import QualityReview

CATEGORIES={'prop':'Objeto simples — bule','stylized_character':'Personagem estilizado — robô','detailed_scene':'Cenário — cadeira','character_user':'Personagem usado no aplicativo — corpo inteiro'}
VARIANTS=['baseline','fast','balanced','quality','triposg']
VIEWS=['front','side','rear','three_quarter']

def comparison_router(data_root):
    root=Path(data_root)/'quality-upgrade'
    character_root=Path(data_root)/'character-advanced-20261011'
    character_directories={'baseline_triposr':'baseline-triposr-quality','triposr_corrected':'triposr-corrected','triposg_quality42':'triposg-quality42','advanced42':'advanced-validated-prototype/candidates/0','advanced43':'advanced-validated-prototype/candidates/1'}
    lock=threading.Lock()
    router=APIRouter(prefix='/api/quality')
    def read(path,default=None):
        return json.loads(path.read_text(encoding='utf-8')) if path.exists() else default
    def file_url(path):
        return '/api/quality/files/'+path.relative_to(root).as_posix() if path.is_file() else None
    def reviews():return read(root/'reviews.json',[])
    def character_url(path):
        return '/api/quality/character-files/'+path.relative_to(character_root).as_posix() if path.is_file() else None
    def character_case():
        evidence=read(character_root/'validation-evidence/evidence.json',{})
        if evidence.get('passed') is not True:return None
        variants=[]
        views=VIEWS+['side_opposite']
        for name,relative in character_directories.items():
            record=evidence.get('variants',{}).get(name)
            if record is None:continue
            directory=character_root/relative
            metadata=read(directory/'inference.json',{})
            if name=='baseline_triposr':metadata=read(directory/'job.json',{}).get('metadata',metadata)
            metadata={**metadata,'integrity':record['integrity']}
            variants.append({'id':name,'metadata':metadata,'fbx':evidence.get('exports',{}).get(name,{}).get('validation'),'renders':{view:character_url(character_root/f'validation-evidence/{name}/textured/qa_{view}.png') for view in views},'clay_renders':{view:character_url(character_root/f'validation-evidence/{name}/clay/qa_{view}.png') for view in views},'albedo_renders':{},'record':character_url(character_root/'validation-evidence/evidence.json'),'model':character_url(directory/'model.glb')})
        return {'id':'hinata','title':'Hinata — antes/depois do modo avançado','reference':character_url(character_root/'advanced-validated-prototype/candidates/0/source.png'),'variants':variants} if variants else None
    def v3_directory(category,variant):
        case='character' if category=='character_user' else category
        name={'triposg':'baseline','triposg_quality':'quality512','triposg_refined':'refined'}[variant]
        if variant=='triposg' and category!='character_user':return None
        return root/'fidelity-v3'/case/name
    def v3_variant(category,variant):
        directory=v3_directory(category,variant)
        if directory is None:return None
        record=read(directory/'v3_record.json')
        if record is None:return None
        render=directory/'clay_v3'
        return {'id':variant,'metadata':{**record['inference'],**record['mesh']},'fbx':record['fbx'],'renders':{view:file_url(render/f'qa_{view}.png') for view in VIEWS},'clay_renders':{view:file_url(render/f'qa_{view}.png') for view in VIEWS},'albedo_renders':{view:None for view in VIEWS},'record':file_url(directory/'v3_record.json'),'model':file_url(directory/'model.glb')}
    @router.get('/comparison')
    def comparison():
        cases=[]
        for category,title in CATEGORIES.items():
            baseline=root/'baseline'/category
            record=read(baseline/'record.json')
            if record is None and category!='character_user':continue
            variants=[]
            for variant in VARIANTS if category!='character_user' else []:
                directory=baseline/'generation' if variant=='baseline' else (root/'triposg/benchmark'/category if variant=='triposg' else root/'improved'/category/variant)
                improved=read(directory/'record.json') if variant!='baseline' else None
                if variant!='baseline' and improved is None:continue
                metadata=record['generation']['metadata'] if variant=='baseline' else {**improved['inference'],**improved['mesh']}
                validation=read(baseline/'export/fbx_validation.json') if variant=='baseline' else improved['fbx']
                render_dir=root/'comparison'/category/variant
                if variant=='triposg':render_dir=root/'comparison'/category/'triposg_clay'
                metadata=dict(metadata)
                metadata['integrity']=read(render_dir/'comparison_report.json',{}).get('after',{}).get('integrity',metadata.get('integrity'))
                variants.append({'id':variant,'metadata':metadata,'fbx':validation,'renders':{view:file_url(render_dir/f'qa_{view}.png') for view in VIEWS},'clay_renders':{view:file_url(root/'comparison'/category/(variant+'_clay')/f'qa_{view}.png') for view in VIEWS},'albedo_renders':{view:file_url(root/'comparison'/category/(variant+'_albedo')/f'qa_{view}.png') for view in VIEWS},'record':file_url(baseline/'record.json' if variant=='baseline' else directory/'record.json'),'model':file_url(directory/'model.glb')})
            for variant in (['triposg'] if category=='character_user' else [])+['triposg_quality','triposg_refined']:
                result=v3_variant(category,variant)
                if result:variants.append(result)
            if not variants:continue
            reference=root/'fidelity-v3/character/baseline/source.png' if category=='character_user' else baseline/'reference.png'
            cases.append({'id':category,'title':title,'reference':file_url(reference),'variants':variants})
        hinata=character_case()
        if hinata:cases.append(hinata)
        return {'cases':cases,'reviews':reviews(),'rubric':{'1':'Falha grave ou recurso inutilizável','2':'Falhas grandes; retrabalho necessário','3':'Utilizável com correções visíveis','4':'Boa correspondência; falhas pequenas','5':'Alta correspondência nas vistas avaliadas'},'notes':'Avaliação humana de imagem única. Verso inferido. TripoSG usa preparo branco/alpha/seed42; TripoSR usa preparo cinza. Geometria neutra remove diferença de materiais. Triângulos e VRAM não são notas de fidelidade.'}
    @router.post('/reviews')
    def save_review(review:QualityReview):
        v3=v3_directory(review.category,review.variant) if review.variant in ['triposg_quality','triposg_refined'] or (review.category=='character_user' and review.variant=='triposg') else None
        record=v3/'v3_record.json' if v3 else root/('baseline/'+review.category+'/record.json' if review.variant=='baseline' else ('triposg/benchmark/'+review.category+'/record.json' if review.variant=='triposg' else 'improved/'+review.category+'/'+review.variant+'/record.json'))
        if review.category=='hinata':
            evidence=read(character_root/'validation-evidence/evidence.json',{})
            if evidence.get('passed') is not True or review.variant not in evidence.get('variants',{}):raise HTTPException(409,'Resultado ainda não foi medido no benchmark.')
        elif not record.is_file():raise HTTPException(409,'Resultado ainda não foi medido no benchmark.')
        value={**review.model_dump(),'updated_at':datetime.now(timezone.utc).isoformat(),'assessment':'manual'}
        with lock:
            root.mkdir(parents=True,exist_ok=True)
            entries=[entry for entry in reviews() if (entry['category'],entry['variant'])!=(review.category,review.variant)]
            entries.append(value)
            temporary=root/'reviews.tmp'
            temporary.write_text(json.dumps(entries,indent=2),encoding='utf-8')
            os.replace(temporary,root/'reviews.json')
        return value
    @router.get('/character-files/{filename:path}')
    def character_file(filename:str):
        base=character_root.resolve();path=(base/filename).resolve()
        if not path.is_relative_to(base) or not path.is_file() or Path(filename).parts[0] not in ['validation-evidence',*{Path(directory).parts[0] for directory in character_directories.values()}] or path.suffix not in ['.png','.glb','.json','.fbx']:
            raise HTTPException(404,'Artefato de personagem não encontrado.')
        return FileResponse(path)
    @router.get('/files/{filename:path}')
    def file(filename:str):
        base=root.resolve();path=(base/filename).resolve()
        if not path.is_relative_to(base) or not path.is_file() or Path(filename).parts[0] not in ['baseline','improved','comparison','triposg','fidelity-v3'] or path.suffix not in ['.png','.glb','.json','.fbx','.zip']:
            raise HTTPException(404,'Artefato de comparação não encontrado.')
        return FileResponse(path)
    return router
