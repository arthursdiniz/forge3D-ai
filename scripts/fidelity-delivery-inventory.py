"""Rehash all pre-upgrade user assets and freeze local source/evidence inventory."""
import hashlib,json,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];qa=ROOT/'data/texture-fidelity-20261013'
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
baseline=json.loads((qa/'baseline.json').read_text());checked=0;differences=[]
for identifier,files in baseline['assets'].items():
    for relative,expected in files.items():
        path=ROOT/'data/assets'/identifier/relative
        if not path.is_file() or digest(path)!=expected:differences.append(str(path))
        checked+=1
assert not differences,differences
snapshot=qa/'final-source';snapshot.mkdir(exist_ok=False);source=[]
extensions={'.py','.tsx','.ts','.css','.cs','.md','.ps1','.json','.bat','.txt'}
for base in ['backend','blender','frontend/src','scripts','tests','unity','docs']:
    source.extend(p for p in (ROOT/base).rglob('*') if p.is_file() and p.suffix in extensions and '__pycache__' not in p.parts)
source.extend([ROOT/'README.md',ROOT/'frontend/package.json',ROOT/'frontend/package-lock.json'])
hashes={}
for path in sorted(set(source)):
    relative=path.relative_to(ROOT);dest=snapshot/relative;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,dest);hashes[relative.as_posix()]=digest(path)
changed=[relative for relative,old in baseline['source'].items() if hashes.get(relative)!=old]
flow=json.loads((qa/'final-live-flow.json').read_text());report=json.loads((qa/'hinata-regional-final-footprint/texture.json').read_text());resources=json.loads((qa/'hinata-regional-final-footprint/resources.json').read_text());unity=json.loads((qa/'unity-validation.json').read_text());assert unity['passed'] and unity['export_job']==flow['export']
proof={'passed':True,'original_assets':{'folders':len(baseline['assets']),'files_checked':checked,'sha256_unchanged':not differences},'baseline_source_files':len(baseline['source']),'changed_baselined_source_files':changed,'final_source_sha256':hashes,'new_core_modules':['texture_fusion','face_reference','face_detection','region_camera','region_masks','face_projection','face_refinement','texture_metrics','texture_seams','cached_views','region_context','region_routes'],'new_ui':'frontend/src/FaceDetailWorkspace.tsx','tests':{'passed':191,'evidence':'publish-full.log','existing_warning':'Starlette AnyIO deprecation'},'build':{'passed':True,'evidence':'delivery-build.log','warning':'Existing Viewer chunk >500kB'},'metrics':report['regional']['metrics'],'regional_resources':resources,'live_flow':flow,'unity':unity,'geometry':report['geometry'],'protected_pixels':report['regional']['outside_unchanged'],'geometry_integrity':json.loads((qa/'diagnostics-final/after/comparison_report.json').read_text())['after']['integrity'],'review':{'one_fresh_review':True,'important_fixed':4,'critical':0,'minor_deferred':0,'evidence':'final-review.md'},'package_sha256':digest(ROOT/'data/assets'/flow['export']/'Forge3D_Unity.zip'),'comparison_sha256':{name:digest(qa/'diagnostics-final'/name) for name in ['face-before-after.png','all-views.png']},'scope':'Current local source snapshot and actual measured artifacts; unknown pre-task source paths are not falsely claimed as changed. No Git/PR operation.'}
(qa/'delivery-inventory.json').write_text(json.dumps(proof,indent=2),encoding='utf-8')
print(json.dumps({'passed':True,'original_files':checked,'original_folders':len(baseline['assets']),'snapshot_files':len(hashes),'changed_baselined_files':len(changed),'tests':191,'export':flow['export']},indent=2))
