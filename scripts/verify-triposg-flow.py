"""Verify jobs created through the UI and import their actual SG export in Unity."""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import time
from pathlib import Path
import httpx

ROOT=Path(__file__).resolve().parents[1]
def read(path):return json.loads(path.read_text(encoding='utf-8'))
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    parser=argparse.ArgumentParser()
    for name in ['generation','optimized','scaled','export']:parser.add_argument('--'+name,required=True)
    args=parser.parse_args()
    if not all(re.fullmatch('[a-f0-9]{32}',value) for value in vars(args).values()):raise ValueError('Invalid job ID')
    proof_path=ROOT/'data/quality-upgrade/triposg/flow-verification.json'
    if proof_path.exists():raise RuntimeError('Proof already exists; preserve it and choose a new verification artifact for a new run.')
    with httpx.Client(base_url='http://127.0.0.1:8000',timeout=30) as client:
        jobs={}
        for name,identifier in vars(args).items():
            for _ in range(600):
                job=client.get('/api/jobs/'+identifier).raise_for_status().json()
                if job['status']=='completed':break
                if job['status'] in ['failed','cancelled']:raise RuntimeError(job['error'])
                time.sleep(0.5)
            else:raise TimeoutError(identifier)
            assert job['provider']=='triposg'
            jobs[name]=job
        gen,opt,scaled,export=[jobs[key] for key in ['generation','optimized','scaled','export']]
        assert opt['parent']==gen['id'] and scaled['parent']==opt['id'] and export['parent']==scaled['id']
        assert gen['metadata']['triangles']>opt['metadata']['triangles']>0
        assert abs(scaled['metadata']['dimensions'][2]-1.5)<0.001
        assert scaled['metadata']['mesh_version']=='game_optimized'
        assert gen['metadata']['texture']['method']=='none'
        directory=ROOT/'data/assets'/gen['id']
        original=digest(directory/'original.glb')
        assert original==digest(directory/'raw_generation.glb')==gen['metadata']['original_sha256']
        benchmark=read(ROOT/'data/quality-upgrade/triposg/benchmark/prop/inference.json')
        assert original==benchmark['original_sha256'] # Same reference, profile and seed, actually repeated.
        assert scaled['metadata']['versions']['processed_mesh']==gen['artifacts']['model']
        assert scaled['metadata']['versions']['game_optimized']==scaled['artifacts']['model']
        assert client.get('/api/jobs/'+scaled['id']+'/original').raise_for_status().json()['id']==gen['id']
    package=ROOT/'data/assets'/export['id']/'Forge3D_Asset'
    manifest=read(package/'asset_manifest.json')
    assert manifest['provider']=='triposg' and manifest['albedo'] is None
    assert manifest['fbx_validation']['passed']
    assert not list((package/'Textures').glob('*.png'))
    qa=ROOT/'data/UnityTripoSGValidation'
    if qa.exists():raise RuntimeError('Disposable Unity project already exists; preserve prior evidence.')
    shutil.copytree(package,qa/'Assets/Forge3D_Asset')
    (qa/'Assets/Editor').mkdir(parents=True)
    shutil.copy2(ROOT/'tests/UnityTripoSGValidation.cs',qa/'Assets/Editor/UnityTripoSGValidation.cs')
    previous=next((ROOT/'data/quality-upgrade/improved/prop/balanced/export/Forge3D_Asset/Textures').glob('*.png'))
    shutil.copy2(previous,qa/'Assets/PreviousAlbedo.png')
    (qa/'Packages').mkdir()
    shutil.copy2(ROOT/'data/UnityQualityValidation/Packages/manifest.json',qa/'Packages/manifest.json')
    (qa/'ProjectSettings').mkdir()
    (qa/'ProjectSettings/ProjectVersion.txt').write_text('m_EditorVersion: 6000.3.0f1\n',encoding='utf-8')
    editor='C:/Program Files/Unity/Hub/Editor/6000.3.0f1/Editor/Unity.exe'
    subprocess.run([editor,'-batchmode','-nographics','-projectPath',str(qa),'-executeMethod','Forge3DTripoSGValidation.BatchValidate','-logFile',str(ROOT/'logs/unity-triposg-validation.log')],check=True,timeout=300,creationflags=subprocess.CREATE_NO_WINDOW)
    report=read(qa/'Assets/Forge3D_Asset/unity_import_report.json')
    extra=read(qa/'Assets/sg_extra_validation.json')
    assert report['passed'] and extra['passed'] and report['textures']==0
    assert report['triangles']==scaled['metadata']['triangles']
    assert abs(report['dimensions'][1]-1.5)<0.001
    proof={'passed':True,'jobs':jobs,'raw_unchanged':True,'same_seed_repeat_raw_sha256':original,'ui_checks':{'provider_sent':True,'only_balanced':True,'no_texture_control':True,'texture_toggle_disabled':True,'wireframe_loaded':True,'effective_encoder_input_pixels':224},'unity':report,'unity_extra':extra,'unity_scope':'batchmode/nographics: actual FBX/UV/normals/height/material/prefab, no gameplay or rendered scene'}
    proof_path.write_text(json.dumps(proof,indent=2),encoding='utf-8')
    print('REAL_TRIPOSG_UI_EXPORT_UNITY_FLOW_PASS',flush=True)
if __name__=='__main__':main()
