"""Immutable two-material regional edit and fresh Unity import, real local runtimes."""
import json
import shutil
import subprocess
import sys
from pathlib import Path
import numpy as np
import trimesh
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.texture_engine.region_camera import RegionCamera
QA=ROOT/'data/texture-fidelity-20261013'
folder=QA/'object-region';folder.mkdir(exist_ok=False)
source=QA/'global-text/model.glb';scene=trimesh.load(source,force='scene',process=False)
names=list(scene.graph.nodes_geometry)
steel=next(i for i,n in enumerate(names) if scene.geometry[scene.graph[n][1]].visual.material.name=='Steel')
camera=RegionCamera(scene,'negative_y',512)
selected=(camera.buffers[2][...,2]==steel+1)&(camera.buffers[0][...,3]>.5)&(camera.buffers[1][...,2]>.75)
ys,xs=np.where(selected);assert len(xs)>100
box=[(xs.min()+3)/512,(ys.min()+3)/512,(xs.max()-3)/512,(ys.max()-3)/512]
ref=camera.image.copy();ref[selected,:3]=[40,175,210];ref[selected,3]=255
(folder/'references/front').mkdir(parents=True);Image.fromarray(ref).save(folder/'references/front/source.png')
(folder/'texture_references.json').write_text(json.dumps({'views':{'front':{'path':'references/front/source.png'}}}),encoding='utf-8')
options={'provider':'reference_region','source_box':box,'target_box':box,'region':'custom','materials':['Steel'],'front_axis':'negative_y','camera_resolution':512,'reviewed_alignment':True,'cached_views':False,'feather_pixels':4}
(folder/'options.json').write_text(json.dumps(options),encoding='utf-8')
with (folder/'trial.log').open('w') as log:
    subprocess.run([str(ROOT/'.venv-texture/Scripts/python.exe'),str(ROOT/'backend/texture_engine/cli.py'),'--input',str(source),'--output',str(folder),'--options',str(folder/'options.json')],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
after=trimesh.load(folder/'model.glb',force='scene',process=False)
materials=lambda s:{m.visual.material.name:m for m in s.geometry.values()}
a,b=materials(scene),materials(after)
proof={'protected_material':'Fabric','edited_material':'Steel','protected_maps':{},'geometry':json.loads((folder/'texture.json').read_text())['geometry']}
for key in ['baseColorTexture','normalTexture','occlusionTexture','metallicRoughnessTexture']:
    proof['protected_maps'][key]=bool(np.array_equal(np.asarray(getattr(a['Fabric'].visual.material,key)),np.asarray(getattr(b['Fabric'].visual.material,key))))
    assert proof['protected_maps'][key],key
assert a['Fabric'].visual.material.alphaMode==b['Fabric'].visual.material.alphaMode=='BLEND'
assert np.array_equal(a['Fabric'].visual.uv,b['Fabric'].visual.uv)
report=json.loads((folder/'texture.json').read_text());assert report['regional']['published']=='candidate' and report['regional']['outside_unchanged']
proof['regional']=report['regional'];(folder/'object-preservation.json').write_text(json.dumps(proof,indent=2),encoding='utf-8')
with (folder/'export.log').open('w') as log:
    subprocess.run([str(ROOT/'tools/blender-4.5.3-windows-x64/blender.exe'),'--background','--factory-startup','--disable-autoexec','--threads','6','--python-exit-code','1','--python',str(ROOT/'blender/pipeline.py'),'--','--input',str(folder/'model.glb'),'--output',str(folder),'--mode','export','--options',str(folder/'options.json')],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
subprocess.run([str(ROOT/'.venv-ai/Scripts/python.exe'),str(ROOT/'backend/texture_engine/validate_export.py'),'--source',str(source),'--directory',str(folder)],cwd=ROOT,check=True)
from backend.worker import Worker
from backend.texture_engine.jobs import texture_metadata
from backend.texture_engine.export_materials import export_materials
import uuid
export_materials(after,folder/'Forge3D_Asset')
Worker(ROOT,None).package({'id':uuid.uuid4().hex,'name':'Two material regional QA','provider':'imported','parent':None,'options':{'pipeline':'URP'}},folder,texture_metadata({'texture_provider':'neural_multiview'},report,options,''))
project=ROOT/'data/UnityTextureFidelityValidation';project.mkdir(exist_ok=False)
(project/'Assets/Editor').mkdir(parents=True);(project/'Packages').mkdir();(project/'ProjectSettings').mkdir();(project/'Library').mkdir()
old=ROOT/'data/UnityTextureFinalValidation'
shutil.copy2(old/'Packages/manifest.json',project/'Packages/manifest.json')
shutil.copy2(old/'Packages/packages-lock.json',project/'Packages/packages-lock.json')
shutil.copy2(old/'ProjectSettings/ProjectVersion.txt',project/'ProjectSettings/ProjectVersion.txt')
shutil.copytree(old/'Library/PackageCache',project/'Library/PackageCache')
flow=json.loads((QA/'final-live-flow.json').read_text())
shutil.copytree(Path(flow['package']),project/'Assets/FaceAsset')
shutil.copytree(folder/'Forge3D_Asset',project/'Assets/ObjectAsset')
shutil.copy2(ROOT/'unity/Forge3DImporter.cs',project/'Assets/Editor/Forge3DImporter.cs')
shutil.copy2(ROOT/'tests/UnityFidelityValidation.cs',project/'Assets/Editor/UnityFidelityValidation.cs')
editor='C:/Program Files/Unity/Hub/Editor/6000.3.0f1/Editor/Unity.exe'
subprocess.run([editor,'-batchmode','-nographics','-projectPath',str(project),'-executeMethod','UnityFidelityValidation.BatchValidate','-logFile',str(project/'fidelity.log')],check=True,timeout=300)
reports={f'{name}_{pipeline}':json.loads((project/'Assets'/name/f'unity_{pipeline}.json').read_text()) for name in ['FaceAsset','ObjectAsset'] for pipeline in ['urp','builtin']}
assert all(r['passed'] for r in reports.values())
(QA/'unity-validation.json').write_text(json.dumps({'passed':True,'mode':'Actual Unity6000.3 batchmode/nographics imports, materials and prefabs; no rendered gameplay claim.','reports':reports},indent=2),encoding='utf-8')
print('FIDELITY_OBJECT_PROTECTED_MAPS_AND_UNITY_URP_BUILTIN_PASS',flush=True)
