"""Validate actual API exports and a measured 2048 benchmark in disposable Unity."""
import json
import shutil
import subprocess
import time
from pathlib import Path
import httpx
ROOT=Path(__file__).resolve().parents[1]
QA=ROOT/'data/UnityQualityValidation'
FLOW=ROOT/'data/quality-upgrade/flow-verification.json'
client=httpx.Client(base_url='http://127.0.0.1:8000',timeout=30)

def wait(identifier):
    for _ in range(1200):
        job=client.get('/api/jobs/'+identifier).raise_for_status().json()
        if job['status']=='completed':return job
        if job['status'] in ['failed','cancelled']:raise RuntimeError(job['error'])
        time.sleep(0.5)
    raise TimeoutError(identifier)

def main():
    flow=json.loads(FLOW.read_text())
    flow['prior_exports']=[flow['high_export']['id'],flow['optimized_export']['id']]
    for key,parent,folder in [('high_export',flow['browser_generation'],'AssetA'),('optimized_export',flow['scaled'],'AssetB')]:
        job=wait(client.post('/api/jobs/'+parent['id']+'/export',json={'pipeline':'URP'}).raise_for_status().json()['id'])
        flow[key]=job
        shutil.copytree(ROOT/'data/assets'/job['id']/'Forge3D_Asset',QA/'Assets'/folder,dirs_exist_ok=True)
    benchmark=ROOT/'data/quality-upgrade/improved/prop/quality'
    report=json.loads((benchmark/'record.json').read_text())
    assert report['fbx']['passed'] and report['inference']['texture']['texture_resolution']==2048
    directory=QA/'Assets/AssetC'
    shutil.copytree(benchmark/'export/Forge3D_Asset',directory,dirs_exist_ok=True)
    (directory/'Editor').mkdir(exist_ok=True)
    source=(ROOT/'unity/Forge3DImporter.cs').read_text(encoding='utf-8')
    (directory/'Editor/Forge3DImporter.cs').write_text(source.replace('public static class Forge3DImporter','public static class Forge3DQualityBenchmarkImporter'),encoding='utf-8')
    texture=next((directory/'Textures').glob('*.png'))
    manifest={'name':'Measured teapot Quality benchmark','editor_class':'Forge3DQualityBenchmarkImporter','pipeline':'URP','model':'Models/Model.fbx','albedo':'Textures/'+texture.name,'fbx_validation':report['fbx'],'source_benchmark':str(benchmark),'inference':report['inference']}
    (directory/'asset_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    shutil.copy2(ROOT/'tests/UnityUrpValidation.cs',QA/'Assets/Editor/Forge3DURPValidation.cs')
    editor=Path('C:/Program Files/Unity/Hub/Editor/6000.3.0f1/Editor/Unity.exe')
    subprocess.run([str(editor),'-batchmode','-nographics','-projectPath',str(QA),'-executeMethod','Forge3DURPValidation.BatchValidate','-logFile',str(ROOT/'logs/unity-quality-final.log')],check=True,timeout=300)
    reports={folder:json.loads((QA/'Assets'/folder/'unity_import_report.json').read_text()) for folder in ['AssetA','AssetB','AssetC']}
    assert all(value['passed'] for value in reports.values())
    assert reports['AssetC']['textureWidth']==2048
    assert abs(reports['AssetB']['dimensions'][1]-1.5)<0.001
    flow['unity_test']={'passed':True,'mode':'batchmode/nographics; import/material/prefab, not rendered gameplay','reports':reports}
    FLOW.write_text(json.dumps(flow,indent=2),encoding='utf-8')
    (ROOT/'data/quality-upgrade/unity-validation.json').write_text(json.dumps(flow['unity_test'],indent=2),encoding='utf-8')
    print('REAL_UNITY_QUALITY_2048_AND_OPTIMIZED_PASS',flush=True)
if __name__=='__main__':main()
