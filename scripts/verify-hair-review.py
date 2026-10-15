"""Final review evidence: actual X-axis hair export and unchanged Kageyama candidate."""
import hashlib,json,subprocess,sys
from pathlib import Path
import numpy as np
import trimesh
from PIL import Image

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.hair.pipeline import reconstruct_hair
from backend.hair.resources import verify_resources

QA=ROOT/'data/hair-upgrade-20261013';trial=QA/'real-kageyama-review-final'
old=trimesh.load(ROOT/'data/assets/d95557822c0b486d8a622218e4eb9810/model.glb',force='scene',process=False)
current=trimesh.load(trial/'candidate/model.glb',force='scene',process=False)
assert set(old.geometry)==set(current.geometry)
unchanged={}
for name,mesh in old.geometry.items():
    other=current.geometry[name]
    channels={'vertices':np.array_equal(mesh.vertices,other.vertices),'faces':np.array_equal(mesh.faces,other.faces),'normals':np.allclose(mesh.vertex_normals,other.vertex_normals,atol=1e-6,rtol=0)}
    if getattr(mesh.visual,'uv',None) is not None:channels['uv']=np.array_equal(mesh.visual.uv,other.visual.uv)
    for field in ['baseColorTexture','normalTexture','occlusionTexture','metallicRoughnessTexture','emissiveTexture']:
        before=getattr(getattr(mesh.visual,'material',None),field,None);after=getattr(getattr(other.visual,'material',None),field,None)
        if before is not None:channels[field]=after is not None and np.array_equal(np.asarray(before),np.asarray(after))
    assert all(channels.values()),(name,channels)
    unchanged[name]=channels
folder=QA/'x-front-real-export';folder.mkdir(exist_ok=False)
source=trimesh.load(ROOT/'data/assets/323051d419ba4e47a4f421fd25e31d5f/model.glb',force='scene',process=False)
matrix=np.array([[0,0,1,0],[0,1,0,0],[-1,0,0,0],[0,0,0,1]],float);source.apply_transform(matrix)
source.export(folder/'source-x.glb',include_normals=True)
analysis=json.loads((trial/'analysis/hair_analysis.json').read_text());analysis['existing_head_field']=np.load(trial/'analysis/existing_head_field.npy',allow_pickle=False);analysis['reference_support_mask']=np.asarray(Image.open(trial/'analysis/reference_aligned_mask.png'))>0
options={'reviewed':True,'front_axis':'x','preset':'auto','attributes':{}}
result,report=reconstruct_hair(source,analysis,options,folder)
errors={}
for name in report['hair_meshes']:
    normals=current.geometry[name].vertex_normals;expected=np.column_stack([normals[:,2],normals[:,1],-normals[:,0]])
    error=float(np.abs(result.geometry[name].vertex_normals-expected).max());errors[name]=error;assert error<=1e-6,(name,error)
result.export(folder/'model.glb',include_normals=True);(folder/'options.json').write_text(json.dumps(options))
with (folder/'export.log').open('w') as log:
    subprocess.run([str(ROOT/'tools/blender-4.5.3-windows-x64/blender.exe'),'--background','--factory-startup','--disable-autoexec','--threads','6','--python-exit-code','1','--python',str(ROOT/'blender/pipeline.py'),'--','--input',str(folder/'model.glb'),'--output',str(folder),'--mode','export','--options',str(folder/'options.json')],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
subprocess.run([str(ROOT/'.venv-ai/Scripts/python.exe'),str(ROOT/'backend/texture_engine/validate_export.py'),'--source',str(folder/'model.glb'),'--directory',str(folder)],cwd=ROOT,check=True)
exports=json.loads((folder/'geometry_export_validation.json').read_text());assert all(exports[name]['equivalent'] for name in ['glb','fbx','obj'])
assert verify_resources(ROOT)['ready']
record={'passed':True,'negative_y_candidate_channels_unchanged':unchanged,'x_generated_normal_max_errors':errors,'x_exports':exports,'scope':'Actual retained Kageyama source rotated via scene transform, generated hair normals rotated once; actual GLB/FBX/OBJ reimports. Existing Unity evidence applies to the unchanged negative_y candidate; X-axis Unity was not rerun.'}
(QA/'review-final-validation.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
proof_path=ROOT/'models/hair/validation.json';proof=json.loads(proof_path.read_text());proof['source_sha256']={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in proof['source_sha256']};proof['evidence']='data/hair-upgrade-20261013/real-kageyama-review-final';proof['review_evidence']='data/hair-upgrade-20261013/review-final-validation.json';proof_path.write_text(json.dumps(proof,indent=2),encoding='utf-8')
print('HAIR_REVIEW_REAL_EXPORT_CHANNELS_PROOF_PASS',flush=True)
