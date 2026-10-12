"""Local interpretation/review endpoints; all detector work runs in a CPU child."""
import asyncio
import hashlib
import io
import json
import os
import threading
import uuid
from pathlib import Path
from fastapi import APIRouter,File,Form,HTTPException,UploadFile
from fastapi.responses import FileResponse
from PIL import Image,ImageOps,UnidentifiedImageError
from pydantic import BaseModel,ConfigDict,Field
from typing import Literal
from .character_understanding import summarize_character,validate_landmarks
from .config import atomic_json


class CharacterCorrection(BaseModel):
    model_config=ConfigDict(extra='forbid')
    category:Literal['humanoid','anime','cartoon','nonhuman','custom']='humanoid'
    pose:Literal['unknown','neutral','a_pose','t_pose','dynamic']='unknown'
    view:Literal['unknown','front','back','left','right']='unknown'
    landmarks:dict[str,dict]=Field(default_factory=dict)
    regions:dict[str,list[float]]=Field(default_factory=dict)
    description:str=Field(default='',max_length=2000)


async def run_detector(root,image,directory,category):
    python=Path(root)/'.venv-character/Scripts/python.exe'
    from .cpu_environment import cpu_environment_ready
    if not cpu_environment_ready(root,'character') or not (Path(root)/'models/character/pose_landmarker_lite.task').is_file():
        raise RuntimeError('Análise de pose não instalada. Configure o recurso local ou use pontos manuais.')
    env=os.environ.copy();env.pop('PYTHONPATH',None);env['PYTHONUTF8']='1'
    process=await asyncio.create_subprocess_exec(str(python),str(Path(root)/'backend/character_analysis_runtime.py'),'--image',str(image),'--output',str(directory),'--category',category,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.STDOUT,env=env,cwd=str(root),creationflags=getattr(__import__('subprocess'),'CREATE_NO_WINDOW',0))
    try:output,_=await asyncio.wait_for(process.communicate(),timeout=45)
    except asyncio.TimeoutError:
        process.kill();await process.communicate();raise RuntimeError('Análise CPU excedeu45s; imagem e interpretação anterior preservadas.')
    (directory/'analysis.log').write_bytes(output)
    if process.returncode:raise RuntimeError('Detector local falhou. Consulte analysis.log; pontos manuais continuam disponíveis.')
    return json.loads((directory/'analysis.json').read_text(encoding='utf-8'))


def character_router(root,data_root):
    router=APIRouter(prefix='/api/character');base=Path(data_root)/'character-analyses';lock=threading.Lock()
    def directory(identifier):
        if len(identifier)!=32 or any(char not in '0123456789abcdef' for char in identifier):raise HTTPException(404,'Interpretação não encontrada.')
        result=base/identifier
        if not (result/'analysis.json').is_file():raise HTTPException(404,'Interpretação não encontrada.')
        return result
    @router.get('/status')
    def status():
        from .cpu_environment import cpu_environment_ready
        ready=cpu_environment_ready(root,'character') and (Path(root)/'models/character/pose_landmarker_lite.task').is_file()
        return {'automatic_pose_available':ready,'manual_points_available':True,'method':'MediaPipe PoseLandmarkerLite CPU' if ready else None,'semantic_segmentation':False,'generative_semantic_conditioning':False,'notes':'Pose editável; cabelo/roupa/acessórios são regiões manuais, sem classificação automática.'}
    @router.post('/analyze',status_code=201)
    async def analyze(image:UploadFile=File(...),category:str=Form('humanoid'),manual_only:bool=Form(False)):
        if category not in ['humanoid','anime','cartoon','nonhuman','custom']:raise HTTPException(422,'Categoria de personagem inválida.')
        content=await image.read(20*1024*1024+1)
        if len(content)>20*1024*1024:raise HTTPException(413,'Imagem excede20MB.')
        try:
            source=Image.open(io.BytesIO(content))
            if source.format not in ['PNG','JPEG','WEBP'] or min(source.size)<16 or source.width*source.height>25_000_000:raise ValueError('Formato/dimensões inválidos.')
            source.load();source=ImageOps.exif_transpose(source).convert('RGBA')
        except (ValueError,OSError,UnidentifiedImageError,Image.DecompressionBombError) as error:raise HTTPException(400,'Imagem inválida: '+str(error))
        identifier=uuid.uuid4().hex;target=base/identifier;target.mkdir(parents=True)
        (target/'source_upload.bin').write_bytes(content);source.save(target/'source.png')
        if manual_only:
            report=summarize_character({},list(source.size),category)
            report.update(method='manual',source_sha256=hashlib.sha256((target/'source.png').read_bytes()).hexdigest(),image_size=list(source.size),detected_poses=0,offline_network_blocked=True,semantic_conditioning=False)
        else:
            try:report=await run_detector(root,target/'source.png',target,category)
            except RuntimeError as error:
                report=summarize_character({},list(source.size),category)
                report.update(method='manual_after_detector_failure',image_size=list(source.size),detector_error=str(error),detected_poses=0,offline_network_blocked=True,semantic_conditioning=False)
        report.update(id=identifier,source_upload_sha256=hashlib.sha256(content).hexdigest(),effective_image_sha256=hashlib.sha256(source.tobytes()).hexdigest(),revision=0,reviewed=False)
        report['source']='/api/character/files/'+identifier+'/source.png'
        report['overlay']='/api/character/files/'+identifier+'/pose_overlay.png' if (target/'pose_overlay.png').is_file() else None
        atomic_json(target/'detector_analysis.json',report);atomic_json(target/'analysis.json',report)
        return report
    @router.get('/analyses/{identifier}')
    def get_analysis(identifier:str):return json.loads((directory(identifier)/'analysis.json').read_text(encoding='utf-8'))
    @router.put('/analyses/{identifier}')
    def correct(identifier:str,correction:CharacterCorrection):
        target=directory(identifier)
        with lock:
            old=json.loads((target/'analysis.json').read_text());detected=json.loads((target/'detector_analysis.json').read_text())
            points={}
            for name,point in correction.landmarks.items():
                original=detected.get('landmarks',{}).get(name)
                if original and original['x']==point.get('x') and original['y']==point.get('y'):points[name]=original
                else:points[name]={**point,'source':'manual','reviewed':True,'visibility':None,'presence':None}
            try:
                points=validate_landmarks(points)
                result=summarize_character(points,old['image_size'],correction.category,correction.pose,correction.view,correction.regions)
            except (ValueError,KeyError,TypeError) as error:raise HTTPException(422,str(error))
            preserved={key:old[key] for key in ['id','source','overlay','source_upload_sha256','effective_image_sha256','image_size','method'] if key in old}
            report={**preserved,**result,'revision':old['revision']+1,'reviewed':True,'description':correction.description,'semantic_conditioning':False,'manual_regions':correction.regions}
            atomic_json(target/'versions'/f"{old['revision']:04d}.json",old);atomic_json(target/'analysis.json',report)
            return report
    @router.get('/files/{identifier}/{filename}')
    def file(identifier:str,filename:str):
        target=directory(identifier)
        if filename not in ['source.png','pose_overlay.png','analysis.json','detector_analysis.json'] or not (target/filename).is_file():raise HTTPException(404,'Arquivo de interpretação não encontrado.')
        return FileResponse(target/filename)
    return router
