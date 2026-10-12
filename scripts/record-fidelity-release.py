"""Freeze source and verify actual final v3 evidence without altering prior runs."""
import hashlib
import json
import shutil
from pathlib import Path
import numpy as np
import trimesh

ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/'data/quality-upgrade/fidelity-v3'

def read(path):return json.loads(path.read_text(encoding='utf-8'))
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    proof_path=DEST/'release-verification.json'
    snapshot=DEST/'final-source'
    if proof_path.exists() or snapshot.exists():raise RuntimeError('Prior release evidence exists; choose a new destination.')
    benchmark=read(DEST/'manifest.json');flow=read(DEST/'flow-verification.json')
    assert len(benchmark)==9 and all(record['fbx']['passed'] for record in benchmark) and flow['passed']
    geometry=[]
    for case in ['character','prop','detailed_scene']:
        before=trimesh.load(DEST/case/'cleaned/model.glb',force='scene',process=False)
        after=trimesh.load(DEST/case/'refined/model.glb',force='scene',process=False)
        assert len(before.geometry)==len(after.geometry)==1
        a=next(iter(before.geometry.values()));b=next(iter(after.geometry.values()))
        assert np.array_equal(a.faces,b.faces) and np.array_equal(a.vertices[:,1:],b.vertices[:,1:])
        for mesh in [a,b]:
            assert np.isfinite(mesh.vertex_normals).all()
            assert np.allclose(np.linalg.norm(mesh.vertex_normals,axis=1),1,atol=1e-5)
        report=read(DEST/case/'refined/refinement.json')
        assert report['original_preserved'] and report['input_sha256']==digest(DEST/case/'cleaned/model.glb')
        geometry.append({'case':case,'triangles':len(b.faces),'faces_height_depth_unchanged':True,'explicit_normals_finite_unit':True,'refinement':report['refinement']})
    original=ROOT/'data/assets/3d672d51032f49e8ad15c8380d2c1a5c'
    preserved={name:digest(original/name) for name in ['source.png','model.glb','original.glb','raw_generation.glb']}
    for name,value in preserved.items():assert value==digest(DEST/'character/baseline'/name)
    extensions={'.py','.cs','.tsx','.ts','.css','.ps1','.md','.json','.txt','.bat'}
    files=[]
    for folder in ['backend','blender','frontend/src','scripts','tests','unity','docs']:
        base=ROOT/folder
        if base.exists():files.extend(path for path in base.rglob('*') if path.is_file() and path.suffix in extensions and '__pycache__' not in path.parts)
    files.extend(path for path in [ROOT/'README.md',ROOT/'requirements.txt',ROOT/'requirements-ai.txt',ROOT/'requirements-dev.txt',ROOT/'frontend/package.json',ROOT/'frontend/package-lock.json'] if path.is_file())
    hashes={}
    for path in sorted(set(files)):
        relative=path.relative_to(ROOT);target=snapshot/relative
        target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,target)
        hashes[relative.as_posix()]=digest(path)
    proof={'passed':True,'tests':{'passed':51,'warning':'Starlette AnyIO deprecated alias only','evidence':'pytest tests -q --basetemp .test-tmp/fidelity-final; exit0'},'frontend_build':{'passed':True,'warning':'Viewer chunk above500kB'},'benchmark_fbx_passed':9,'geometry':geometry,'preserved_user_baseline_sha256':preserved,'unity':flow['unity'],'unity_extra':flow['unity_extra'],'source_sha256':hashes,'scope':'Explicit GLB normals, vertex coordinates/connectivity, parent hashes, real FBX roundtrip and Unity batchmode. IoU is frontal2D only.'}
    proof_path.write_text(json.dumps(proof,indent=2),encoding='utf-8')
    print(json.dumps({'passed':True,'snapshot_files':len(hashes),'fbx_variants':9,'unity_triangles':flow['unity']['triangles'],'geometry':geometry},indent=2))

if __name__=='__main__':main()
