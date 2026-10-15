"""Actual post-upgrade neural image and text trials; originals are never overwritten."""
import json
import shutil
import subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];qa=ROOT/'data/semantic-upgrade-20261014/regression-global'
cases=[('global-image',ROOT/'data/assets/d50d2f098559482ca796bb59672b7289/model.glb',{'provider':'neural_multiview','resolution':4096,'uv_mode':'preserve','front_axis':'negative_y','prompt':'anime volleyball player with orange hair, black and orange uniform, number 10','style':'anime','seed':44,'fusion':'robust'}),('global-text',ROOT/'data/texture-engine-20261012/object-flow/store/assets/cf523b4df54e43a98133e0b9a51536cb/model.glb',{'provider':'neural_multiview','conditioning':'text','resolution':1024,'uv_mode':'preserve','front_axis':'negative_y','prompt':'a two part game prop, larger red painted wooden block next to a smaller brushed steel block, coherent surface colors, no text','style':'stylized','seed':21,'fusion':'robust'})]
for name,source,options in cases:
    folder=qa/name;folder.mkdir(exist_ok=False);bundle={}
    if name=='global-image':
        reference=folder/'references/front';reference.mkdir(parents=True);shutil.copy2(ROOT/'data/test-inputs/hinata-shoyo-reference-20261011.png',reference/'source.png');bundle={'front':{'path':'references/front/source.png'}}
    (folder/'texture_references.json').write_text(json.dumps({'views':bundle}),encoding='utf-8');(folder/'options.json').write_text(json.dumps(options),encoding='utf-8')
    with (folder/'trial.log').open('w',encoding='utf-8') as log:result=subprocess.run([str(ROOT/'.venv-texture/Scripts/python.exe'),str(ROOT/'backend/texture_engine/cli.py'),'--input',str(source),'--output',str(folder),'--options',str(folder/'options.json')],stdout=log,stderr=subprocess.STDOUT,cwd=ROOT)
    assert result.returncode==0,'Real neural trial failed: '+str(folder/'trial.log')
    report=json.loads((folder/'texture.json').read_text());assert report['geometry']['equivalent'] and report['neural']['offline'] and report['neural']['joint_views']==6 and report['fusion_mode']=='robust'
    print(name+' REAL_NEURAL_PASS '+str(report['neural']['inference_seconds'])+'s',flush=True)
    with (folder/'export.log').open('w',encoding='utf-8') as log:result=subprocess.run([str(ROOT/'tools/blender-4.5.3-windows-x64/blender.exe'),'--background','--factory-startup','--disable-autoexec','--threads','6','--python-exit-code','1','--python',str(ROOT/'blender/pipeline.py'),'--','--input',str(folder/'model.glb'),'--output',str(folder),'--mode','export','--options',str(folder/'options.json')],stdout=log,stderr=subprocess.STDOUT,cwd=ROOT)
    assert result.returncode==0,'Neural export failed.'
    result=subprocess.run([str(ROOT/'.venv-ai/Scripts/python.exe'),str(ROOT/'backend/texture_engine/validate_export.py'),'--source',str(source),'--directory',str(folder)],cwd=ROOT);assert result.returncode==0
print('UPGRADED_GLOBAL_IMAGE_TEXT_EXPORT_PASS',flush=True)
