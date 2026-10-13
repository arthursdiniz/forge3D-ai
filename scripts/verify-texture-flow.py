"""Actual import→independent texture→export fixture and immutable geometry proof."""
import hashlib
import io
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
import trimesh
from PIL import Image
from backend.texture_engine.uv import prepare_uv
from backend.texture_engine.identity import compare_geometry
from backend.app import create_app
from backend.worker import Worker
from fastapi.testclient import TestClient

directory=ROOT/'data/texture-engine-20261012/object-flow';directory.mkdir(parents=True,exist_ok=True)
scene=trimesh.Scene()
for name,offset,scale in [('Fabric',[0,0,0],[.5,1.1,.4]),('Steel',[.55,0,0],[.4,.6,.5])]:
    mesh=trimesh.creation.box(extents=scale);mesh.apply_translation(offset);scene.add_geometry(mesh,geom_name=name,node_name=name)
scene,_=prepare_uv(scene,'new',1024)
for index,mesh in enumerate(scene.geometry.values()):
    mesh.visual.material=trimesh.visual.material.PBRMaterial(name=['Fabric','Steel'][index],baseColorTexture=Image.new('RGBA',(16,16),[(255,0,0,230),(128,128,128,255)][index]),normalTexture=Image.new('RGB',(16,16),(128,128,255)) if index==0 else None,metallicRoughnessTexture=Image.new('RGBA',(16,16),(0,64,128,255)) if index==0 else None,occlusionTexture=Image.new('RGB',(16,16),(220,220,220)) if index==0 else None,metallicFactor=[.5,.9][index],roughnessFactor=[.8,.2][index],alphaMode='BLEND' if index==0 else 'OPAQUE')
fixture=directory/'two-material-object.glb';scene.export(fixture,include_normals=True);digest=hashlib.sha256(fixture.read_bytes()).hexdigest()
app=create_app(directory/'store',start_worker=False);store=app.state.store;client=TestClient(app);worker=Worker(ROOT,store)
response=client.post('/api/models/import',files={'model':('object.glb',fixture.read_bytes(),'model/gltf-binary')});assert response.status_code==201,response.text
parent=response.json();worker.process_job(parent);assert store.get(parent['id'])['status']=='completed'
source=store.directory(parent['id'])/'model.glb';source_digest=hashlib.sha256(source.read_bytes()).hexdigest()
image=Image.new('RGBA',(128,128),(0,0,0,0));image.paste((220,60,30,255),(8,8,120,120));buffer=io.BytesIO();image.save(buffer,format='PNG')
response=client.post(f"/api/jobs/{parent['id']}/texture",data={'options':json.dumps({'resolution':1024,'uv_mode':'preserve'})},files={'front':('front.png',buffer.getvalue(),'image/png')});assert response.status_code==201,response.text
texture=response.json();worker.process_job(texture);assert store.get(texture['id'])['status']=='completed'
assert hashlib.sha256(source.read_bytes()).hexdigest()==source_digest and hashlib.sha256(fixture.read_bytes()).hexdigest()==digest
response=client.post(f"/api/jobs/{texture['id']}/export",json={'pipeline':'URP'});assert response.status_code==201,response.text
export=response.json();worker.process_job(export);assert store.get(export['id'])['status']=='completed'
target=store.directory(export['id']);before=trimesh.load(source,force='scene',process=False)
comparisons={}
for name,path in [('texture',store.directory(texture['id'])/'model.glb'),('export_glb',target/'Forge3D_Asset/Models/Model.glb'),('fbx_reimport',target/'fbx_reimport.glb')]:
    comparison=compare_geometry(before,trimesh.load(path,force='scene',process=False));assert comparison['equivalent'],comparison;comparisons[name]=comparison
report={'import':parent['id'],'texture':texture['id'],'export':export['id'],'package':str(target/'Forge3D_Asset'),'source_immutable':True,'comparisons':comparisons}
(directory/'result.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))
