"""Verify actual v3 jobs and their exported FBX in a disposable Unity project."""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path
import httpx

ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/'data/quality-upgrade/fidelity-v3'

def read(path):return json.loads(path.read_text(encoding='utf-8'))
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    parser=argparse.ArgumentParser()
    names=['generation','cleaned','refined','optimized','scaled','export']
    for name in names:parser.add_argument('--'+name,required=True)
    args=parser.parse_args()
    if not all(re.fullmatch('[a-f0-9]{32}',value) for value in vars(args).values()):raise ValueError('Invalid job ID')
    proof_path=DEST/'flow-verification.json'
    qa=ROOT/'data/UnityFidelityV3Validation'
    if proof_path.exists() or qa.exists():raise RuntimeError('Preserve prior evidence; use a new verification destination for a new run.')
    with httpx.Client(base_url='http://127.0.0.1:8000',timeout=30) as client:
        jobs={name:client.get('/api/jobs/'+getattr(args,name)).raise_for_status().json() for name in names}
        gen,clean,refined,opt,scaled,export=[jobs[name] for name in names]
        assert all(job['status']=='completed' and job['provider']=='triposg' for job in jobs.values())
        for parent,child in zip(names,names[1:]):assert jobs[child]['parent']==jobs[parent]['id']
        assert gen['options']['quality']=='quality' and gen['metadata']['effective_settings']['mc_resolution']==512
        assert clean['options']['operation']=='cleanup' and refined['options']['operation']=='refine_silhouette'
        fit=refined['metadata']['refinement']
        assert fit['accepted'] and fit['silhouette_iou_after']>fit['silhouette_iou_before']
        assert fit['faces_changed']==0 and not fit['depth_changed'] and not fit['height_changed']
        assert gen['metadata']['triangles']>=clean['metadata']['triangles']==refined['metadata']['triangles']>opt['metadata']['triangles']>0
        assert all('refinement' not in job['metadata'] for job in [opt,scaled,export])
        assert abs(scaled['metadata']['dimensions'][2]-1.5)<0.001
        assert scaled['metadata']['mesh_version']=='game_optimized'
        assert gen['metadata']['texture']['method']=='none'
        directory=ROOT/'data/assets'/gen['id']
        raw_hash=digest(directory/'original.glb')
        assert raw_hash==digest(directory/'raw_generation.glb')==gen['metadata']['original_sha256']
        for parent,child in [('generation','cleaned'),('cleaned','refined')]:
            report=read(ROOT/'data/assets'/jobs[child]['id']/'refinement.json')
            assert report['original_preserved'] and report['input_sha256']==digest(ROOT/'data/assets'/jobs[parent]['id']/'model.glb')
        assert scaled['metadata']['versions']['processed_mesh']==refined['artifacts']['model']
        assert scaled['metadata']['versions']['game_optimized']==scaled['artifacts']['model']
        assert client.get('/api/jobs/'+scaled['id']+'/original').raise_for_status().json()['id']==gen['id']
        response=client.get(export['artifacts']['unity_zip']).raise_for_status()
        assert response.content[:2]==b'PK'
    package=ROOT/'data/assets'/export['id']/'Forge3D_Asset'
    manifest=read(package/'asset_manifest.json')
    assert manifest['provider']=='triposg' and manifest['albedo'] is None and manifest['fbx_validation']['passed']
    assert not list((package/'Textures').glob('*.png'))
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
    subprocess.run([editor,'-batchmode','-nographics','-projectPath',str(qa),'-executeMethod','Forge3DTripoSGValidation.BatchValidate','-logFile',str(ROOT/'logs/unity-fidelity-v3-validation.log')],check=True,timeout=600,creationflags=subprocess.CREATE_NO_WINDOW)
    report=read(qa/'Assets/Forge3D_Asset/unity_import_report.json')
    extra=read(qa/'Assets/sg_extra_validation.json')
    assert report['passed'] and extra['passed'] and report['textures']==0
    assert report['triangles']==scaled['metadata']['triangles']
    assert abs(report['dimensions'][1]-1.5)<0.001
    proof={'passed':True,'jobs':jobs,'raw_unchanged':True,'original_sha256':raw_hash,'unity':report,'unity_extra':extra,'unity_scope':'batchmode/nographics: actual FBX/UV/nonzero finite normals/height/material/prefab; no gameplay or rendered scene'}
    proof_path.write_text(json.dumps(proof,indent=2),encoding='utf-8')
    print('REAL_FIDELITY_V3_EXPORT_UNITY_FLOW_PASS',flush=True)

if __name__=='__main__':main()
