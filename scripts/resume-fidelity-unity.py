"""Resume the already completed object run at package/Unity, without regenerating it."""
import json,shutil,subprocess,sys,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.worker import Worker
from backend.texture_engine.jobs import texture_metadata
from backend.texture_engine.export_materials import export_materials
import trimesh
qa=ROOT/'data/texture-fidelity-20261013';folder=qa/'object-region';report=json.loads((folder/'texture.json').read_text());options=json.loads((folder/'options.json').read_text())
export_materials(trimesh.load(folder/'model.glb',force='scene',process=False),folder/'Forge3D_Asset')
Worker(ROOT,None).package({'id':uuid.uuid4().hex,'name':'Two material regional QA','provider':'imported','parent':None,'options':{'pipeline':'URP'}},folder,texture_metadata({'texture_provider':'neural_multiview'},report,options,''))
project=ROOT/'data/UnityTextureFidelityValidation'
shutil.copytree(folder/'Forge3D_Asset',project/'Assets/ObjectAsset',dirs_exist_ok=True)
shutil.copy2(ROOT/'tests/UnityFidelityValidation.cs',project/'Assets/Editor/UnityFidelityValidation.cs')
subprocess.run(['C:/Program Files/Unity/Hub/Editor/6000.3.0f1/Editor/Unity.exe','-batchmode','-nographics','-projectPath',str(project),'-executeMethod','UnityFidelityValidation.BatchValidate','-logFile',str(project/'fidelity-resume.log')],check=True,timeout=180)
reports={f'{name}_{pipeline}':json.loads((project/'Assets'/name/f'unity_{pipeline}.json').read_text()) for name in ['FaceAsset','ObjectAsset'] for pipeline in ['urp','builtin']}
assert all(r['passed'] for r in reports.values())
(qa/'unity-validation.json').write_text(json.dumps({'passed':True,'mode':'Actual Unity6000.3 batchmode/nographics imports, materials and prefabs; no rendered gameplay claim.','reports':reports},indent=2),encoding='utf-8')
print('FIDELITY_OBJECT_PROTECTED_MAPS_AND_UNITY_URP_BUILTIN_PASS',flush=True)
