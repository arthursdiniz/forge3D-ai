"""Preservation and release evidence for the completed local character upgrade."""
import hashlib
import json
import shutil
from pathlib import Path
import sys
import numpy as np
import trimesh
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.storage import Store
from backend.hunyuan_provider import HunyuanMiniProvider

def digest(path):
    result=hashlib.sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda:source.read(1024*1024),b''):result.update(chunk)
    return result.hexdigest()
def read(path):return json.loads(path.read_text(encoding='utf-8'))

def main():
    base=ROOT/'data/character-advanced-20261011';target=base/'release-verification.json'
    if target.exists():raise RuntimeError('Preserve prior release proof.')
    store=Store(ROOT/'data');old=ROOT/'data/assets/51764b49c97743508f5391760330dc1f'
    original={}
    for name in ['model.glb','original.glb','raw_generation.glb','source.png','prepared.png','inference.json','mesh_report.json']:
        assert digest(old/name)==digest(base/'baseline-triposr-quality'/name)
        original[name]=digest(old/name)
    reference=ROOT/'data/test-inputs/hinata-shoyo-reference-20261011.png'
    assert digest(reference)=='5003a9a4c73a99d72902fd6f732de211d37aa62754d0ec1162c08a5fef6fa454'
    fixed=ROOT/'data/assets/aa70f55494cc422fa10acb0a1b89e334/model.glb'
    source=trimesh.load(old/'model.glb',force='scene',process=False).to_geometry()
    repaired=trimesh.load(fixed,force='scene',process=False).to_geometry()
    def corner_signature(mesh):
        return sorted(tuple(sorted(tuple(np.round(np.r_[mesh.vertices[i],mesh.visual.uv[i]],6)) for i in face)) for face in mesh.faces)
    assert corner_signature(source)==corner_signature(repaired)
    assert len(source.faces)==len(repaired.faces)==57126
    normals_job=store.get('aa70f55494cc422fa10acb0a1b89e334')
    assert normals_job['status']=='completed' and normals_job['metadata']['integrity'][0]['orientation']=='outward_closed'
    flow=read(base/'ui-flow-verification.json');assert flow['passed']
    unity_export=ROOT/'data/assets/e1f431f373db43db865c418b62301122/Forge3D_Unity.zip'
    assert digest(unity_export)==digest(base/'Forge3D-Hinata-Advanced-Unity.zip')
    batch=store.get('050aa8e345fb4260b679b851e8c8d3ab')
    monitor=read(ROOT/'data/assets'/batch['id']/'gpu_monitor.json')
    total_peak=max(sample['gpu_used_mb'] for sample in monitor['samples'])
    evidence=read(base/'validation-evidence/evidence.json');assert evidence['passed']
    assert all((base/'validation-evidence/optimized43'/f'qa_{view}.png').is_file() for view in ['front','side','side_opposite','rear','three_quarter'])
    snapshot=base/'release-source';snapshot.mkdir()
    sources=list((ROOT/'backend').glob('*.py'))+list((ROOT/'frontend/src').glob('*'))+list((ROOT/'blender').glob('*.py'))+list((ROOT/'unity').glob('*.cs'))+list((ROOT/'tests').glob('test_*character*.py'))
    sources += [ROOT/'tests/test_blender_normal_orientation.py',ROOT/'tests/test_candidate_publication.py',ROOT/'README.md',ROOT/'docs/CHARACTER_ADVANCED_VALIDATION.md',ROOT/'docs/PROGRESS.md',ROOT/'docs/QA.md',ROOT/'docs/MODELS.md',ROOT/'requirements-hunyuan-trial-lock.txt']
    files={}
    for path in sources:
        if path.is_file():
            relative=path.relative_to(ROOT);copy=snapshot/relative;copy.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,copy);files[relative.as_posix()]=digest(path)
    proof={'passed':True,'input_sha256':digest(reference),'old_hinata_files_unchanged':original,'original_user_jobs_preserved':['51764b49c97743508f5391760330dc1f','d3c2aa9678a94dbc83f37d1a683dab7c','382e5cb47d1a4f29a570858de821f939'],'normal_operation_preserves_corner_positions_uvs':True,'normal_operation_job':normals_job,'generation_wall_seconds':batch['metadata']['advanced']['generation_wall_seconds'],'peak_pytorch_mb':batch['metadata']['advanced']['peak_vram_mb'],'peak_total_gpu_mb':total_peak,'provider':HunyuanMiniProvider(ROOT).health_check(),'unity':flow['unity'],'zip_sha256':digest(unity_export),'source_files':files,'scope':'One Hinata reference, confirmed RTX4060, no offload. Visual limitation and anatomy uncertainty documented; no rig/gameplay proof.'}
    assert proof['provider']['presets']==['balanced','quality','advanced']
    assert all(store.get(identifier) is not None for identifier in proof['original_user_jobs_preserved'])
    target.write_text(json.dumps(proof,indent=2),encoding='utf-8')
    print('CHARACTER_RELEASE_HASH_PRESERVATION_AND_UNITY_PASS',flush=True)
if __name__=='__main__':main()
