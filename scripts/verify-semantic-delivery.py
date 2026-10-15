"""Fresh exports/packages and old-feature regression after semantic integration."""
import json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];QA=ROOT/'data/semantic-upgrade-20261014'
sys.path.insert(0,str(ROOT))
from backend.worker import Worker
worker=Worker(ROOT,None)
def run(args,log):
    with log.open('w',encoding='utf-8') as stream:subprocess.run(args,cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,check=True)
packages={}
for name,folder,source in [
 ('KageSemantic',QA/'A-kageyama/result',ROOT/'data/assets/323051d419ba4e47a4f421fd25e31d5f/model.glb'),
 ('HinataSemantic',QA/'B-hinata-head/result',ROOT/'data/assets/3c2829b70fe046328b86d2a1141736d4/model.glb'),
 ('StylizedSemantic',QA/'C-stylized-naruto/result',QA/'C-stylized-baseline/model.glb'),
 ('UniformSemantic',QA/'B-uniform-real-multiview/result3',ROOT/'data/assets/323051d419ba4e47a4f421fd25e31d5f/model.glb'),
 ('NeuralSemantic',QA/'neural-completion-real',ROOT/'data/assets/323051d419ba4e47a4f421fd25e31d5f/model.glb')]:
    if name=='UniformSemantic':
        folder.mkdir(exist_ok=False);previous=folder.parent/'result2';options=json.loads((previous/'options.json').read_text());(folder/'options.json').write_text(json.dumps(options))
        run([str(ROOT/'.venv-texture/Scripts/python.exe'),str(ROOT/'backend/texture_engine/semantic_cli.py'),'--mode','paint','--input',str(source),'--output',str(folder),'--options',str(folder/'options.json'),'--analysis',str(folder.parent/'analysis')],folder/'process.log')
    run([str(ROOT/'tools/blender-4.5.3-windows-x64/blender.exe'),'--background','--factory-startup','--disable-autoexec','--threads','6','--python-exit-code','1','--python',str(ROOT/'blender/pipeline.py'),'--','--input',str(folder/'model.glb'),'--output',str(folder),'--mode','export','--options',str(folder/'options.json')],folder/'delivery-export.log')
    run([str(ROOT/'.venv-ai/Scripts/python.exe'),str(ROOT/'backend/texture_engine/validate_export.py'),'--source',str(source),'--directory',str(folder)],folder/'delivery-validation.log')
    run([str(ROOT/'.venv-ai/Scripts/python.exe'),str(ROOT/'backend/texture_engine/export_materials.py'),'--input',str(folder/'model.glb'),'--output',str(folder/'Forge3D_Asset')],folder/'delivery-materials.log')
    report=json.loads((folder/'texture.json').read_text());worker.package({'id':name.lower(),'name':name,'provider':'imported','parent':None,'options':{'pipeline':'URP'}},folder,{'texture':report})
    packages[name]=str((folder/'Forge3D_Asset').relative_to(ROOT));print('SEMANTIC_ACTUAL_EXPORT_PACKAGE_PASS',name,flush=True)
(QA/'packages.json').write_text(json.dumps(packages,indent=2))
print('SEMANTIC_FIVE_PACKAGES_PASS',flush=True)
