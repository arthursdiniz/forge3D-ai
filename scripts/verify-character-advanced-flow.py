"""Verify real UI jobs, source/RAW preservation and actual exported FBX in Unity."""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path
import httpx
ROOT=Path(__file__).resolve().parents[1]
def read(path):return json.loads(path.read_text(encoding='utf-8'))
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    parser=argparse.ArgumentParser()
    for name in ['generation','candidate','optimized','scaled','export']:parser.add_argument('--'+name,required=True)
    args=parser.parse_args()
    assert all(re.fullmatch('[a-f0-9]{32}',value) for value in vars(args).values())
    proof_path=ROOT/'data/character-advanced-20261011/ui-flow-verification.json'
    if proof_path.exists():raise RuntimeError('Preserve prior evidence; choose a new verification artifact.')
    with httpx.Client(base_url='http://127.0.0.1:8000',timeout=30) as client:
        jobs={name:client.get('/api/jobs/'+identifier).raise_for_status().json() for name,identifier in vars(args).items()}
        assert all(job['status']=='completed' and job['provider']=='hunyuan_mini' for job in jobs.values())
        gen,candidate,opt,scaled,export=[jobs[key] for key in ['generation','candidate','optimized','scaled','export']]
        assert candidate['parent']==gen['id'] and opt['parent']==candidate['id'] and scaled['parent']==opt['id'] and export['parent']==scaled['id']
        assert candidate['metadata']['candidate_index']==1 and candidate['metadata']['seed']==43
        assert gen['metadata']['advanced']['candidate_count']==2
        assert gen['metadata']['triangles']>opt['metadata']['triangles']>0
        assert abs(scaled['metadata']['dimensions'][2]-1.5)<.001
        assert 'refinement' not in scaled['metadata'] # stale contour measurements must not survive transforms.
        assert scaled['metadata']['mesh_version']=='game_optimized'
        assert scaled['metadata']['versions']['processed_mesh']==candidate['artifacts']['model']
        assert client.get('/api/jobs/'+scaled['id']+'/original').raise_for_status().json()['id']==candidate['id']
        originals={}
        for choice in gen['metadata']['character_candidates']:
            directory=ROOT/'data/assets'/choice['id']
            raw=digest(directory/'raw_generation.glb');assert raw==digest(directory/'original.glb')
            metadata=read(directory/'inference.json');assert raw==metadata['original_sha256']
            assert metadata['seed']==choice['seed']
            originals[str(choice['seed'])]=raw
        assert originals['42']!=originals['43']
        reference=ROOT/'data/test-inputs/hinata-shoyo-reference-20261011.png'
        assert digest(reference)==digest(ROOT/'data/assets'/gen['id']/'source_upload.bin')
    package=ROOT/'data/assets'/export['id']/'Forge3D_Asset'
    manifest=read(package/'asset_manifest.json')
    assert manifest['provider']=='hunyuan_mini' and manifest['albedo'] and manifest['fbx_validation']['passed']
    qa=ROOT/'data/UnityCharacterAdvancedValidation'
    if qa.exists():raise RuntimeError('Disposable Unity project already exists; preserve prior evidence.')
    shutil.copytree(package,qa/'Assets/Forge3D_Asset')
    (qa/'Assets/Editor').mkdir(parents=True)
    shutil.copy2(ROOT/'tests/UnityCharacterAdvancedValidation.cs',qa/'Assets/Editor/UnityCharacterAdvancedValidation.cs')
    (qa/'Packages').mkdir()
    (qa/'Packages/manifest.json').write_text(json.dumps({'dependencies':{'com.unity.render-pipelines.universal':'17.3.0','com.unity.modules.jsonserialize':'1.0.0','com.unity.modules.imageconversion':'1.0.0'}}),encoding='utf-8')
    (qa/'ProjectSettings').mkdir()
    (qa/'ProjectSettings/ProjectVersion.txt').write_text('m_EditorVersion: 6000.3.0f1\n',encoding='utf-8')
    editor='C:/Program Files/Unity/Hub/Editor/6000.3.0f1/Editor/Unity.exe'
    subprocess.run([editor,'-batchmode','-nographics','-projectPath',str(qa),'-executeMethod','Forge3DCharacterAdvancedValidation.BatchValidate','-logFile',str(ROOT/'logs/unity-character-advanced-validation.log')],check=True,timeout=600,creationflags=subprocess.CREATE_NO_WINDOW)
    report=read(qa/'Assets/Forge3D_Asset/unity_import_report.json')
    extra=read(qa/'Assets/character_extra_validation.json')
    assert report['passed'] and extra['passed'] and report['textures']==1
    assert report['triangles']==scaled['metadata']['triangles'] and abs(report['dimensions'][1]-1.5)<.001
    proof={'passed':True,'jobs':jobs,'raw_unchanged':True,'candidate_raw_sha256':originals,'input_sha256':digest(reference),'unity':report,'unity_extra':extra,'unity_scope':'batchmode/nographics: actual FBX/UV/normals/height/material/texture/prefab; no rig/gameplay or rendered scene'}
    proof_path.write_text(json.dumps(proof,indent=2),encoding='utf-8')
    print('REAL_CHARACTER_UI_EXPORT_UNITY_FLOW_PASS',flush=True)
if __name__=='__main__':main()
