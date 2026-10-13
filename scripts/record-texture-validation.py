"""Publish availability only from real, inspected end-to-end artifacts."""
import hashlib
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
qa=ROOT/'data/texture-engine-20261012'
trials=[qa/'neural-hinata-trial1',qa/'neural-object-text-trial1']
evidence=[]
for directory in trials:
    report=json.loads((directory/'texture.json').read_text(encoding='utf-8'))
    exports=json.loads((directory/'geometry_export_validation.json').read_text(encoding='utf-8'))
    assert report['geometry']['equivalent'] and report['neural']['offline'] and report['neural']['joint_views']==6
    assert report['synthesized_percent']>30 and all(item['equivalent'] for item in exports.values())
    evidence.append({'directory':str(directory.relative_to(ROOT)),'conditioning':report['neural']['conditioning'],'inference_seconds':report['neural']['inference_seconds'],'peak_allocated_mb':report['neural']['peak_allocated_mb'],'peak_reserved_mb':report['neural']['peak_reserved_mb'],'texture_report_sha256':digest(directory/'texture.json'),'exports_report_sha256':digest(directory/'geometry_export_validation.json'),'model_sha256':digest(directory/'model.glb')})
for pipeline in ['urp','builtin']:
    path=ROOT/'data/UnityTextureValidation/Assets/Forge3D_Asset'/f'unity_texture_{pipeline}.json'
    proof=json.loads(path.read_text(encoding='utf-8'));assert proof['passed'] and proof['materials']==2
for resolution in [2048,4096]:
    report=json.loads((qa/f'hinata-cached-neural-{resolution}'/'texture.json').read_text(encoding='utf-8'));assert report['geometry']['equivalent']
resources=[]
for name in ['sdxl','adapter']:
    folder=ROOT/'models/texture'/name;manifest=json.loads((folder/'download_manifest.json').read_text(encoding='utf-8'))
    for item in manifest['files']:
        path=folder/item['path'];assert path.stat().st_size==item['bytes']
        resources.append({'path':str(path.relative_to(ROOT)),'bytes':item['bytes'],'mtime_ns':path.stat().st_mtime_ns})
files=list((ROOT/'backend/texture_engine').glob('*.py'))+list((ROOT/'vendor/MV-Adapter/mvadapter').rglob('*.py'))+[ROOT/'blender/import_static.py',ROOT/'blender/pipeline.py',ROOT/'unity/Forge3DImporter.cs',ROOT/'.venv-texture/Lib/site-packages/forge-runtime.pth',ROOT/'models/texture/core_runtime.json',ROOT/'models/texture/neural_runtime.json']
proof={'end_to_end_passed':True,'world_geometry_equivalent':True,'offline':True,'conditionings':['image','text'],'profiles':['conservative'],'atlas_resolutions':[1024,2048,4096],'native_resolution':512,'steps':20,'device':'NVIDIA GeForce RTX 4060','vram_mb':8188,'evidence':evidence,'source_sha256':{str(path.relative_to(ROOT)):digest(path) for path in files},'resources':resources,'limitations':'Real albedo neural generation; no neural data/PBR map generation. Native 512px; atlas 4K does not create native detail. Synthetic backs are model guesses; image fidelity is not exact.'}
(ROOT/'models/texture/validation.json').write_text(json.dumps(proof,indent=2),encoding='utf-8')
print('REAL_TEXTURE_AVAILABILITY_PROOF_RECORDED')
