"""Real post-review composition, chained licenses, exports; existing artifacts retained."""
import json,hashlib,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];QA=ROOT/'data/semantic-upgrade-20261014';sys.path.insert(0,str(ROOT))
from backend.worker import Worker
from backend.storage import Store
from backend.texture_engine.jobs import texture_metadata
store=Store(ROOT/'data');worker=Worker(ROOT,store)
def run(args,log):
    with log.open('w',encoding='utf-8') as stream:subprocess.run(args,cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,check=True)
def paint(source,analysis,folder,options):
    folder.mkdir(exist_ok=False);(folder/'options.json').write_text(json.dumps(options))
    run([str(ROOT/'.venv-texture/Scripts/python.exe'),str(ROOT/'backend/texture_engine/semantic_cli.py'),'--mode','paint','--input',str(source),'--output',str(folder),'--options',str(folder/'options.json'),'--analysis',str(analysis)],folder/'process.log')
    report=json.loads((folder/'texture.json').read_text());assert report['geometry']['equivalent'] and report['semantic']['protected_pixels_equal'];return report
def export(name,folder,source,parent):
    run([str(ROOT/'tools/blender-4.5.3-windows-x64/blender.exe'),'--background','--factory-startup','--disable-autoexec','--threads','6','--python-exit-code','1','--python',str(ROOT/'blender/pipeline.py'),'--','--input',str(folder/'model.glb'),'--output',str(folder),'--mode','export','--options',str(folder/'options.json')],folder/'post-review-export.log')
    run([str(ROOT/'.venv-ai/Scripts/python.exe'),str(ROOT/'backend/texture_engine/validate_export.py'),'--source',str(source),'--directory',str(folder)],folder/'post-review-validation.log')
    run([str(ROOT/'.venv-ai/Scripts/python.exe'),str(ROOT/'backend/texture_engine/export_materials.py'),'--input',str(folder/'model.glb'),'--output',str(folder/'Forge3D_Asset')],folder/'post-review-materials.log')
    report=json.loads((folder/'texture.json').read_text());metadata=texture_metadata(parent,report,json.loads((folder/'options.json').read_text()),hashlib.sha256(source.read_bytes()).hexdigest());(folder/'post-review-metadata.json').write_text(json.dumps(metadata,indent=2))
    worker.package({'id':name.lower(),'name':name,'provider':'imported','parent':None,'options':{}},folder,metadata);return metadata
source=ROOT/'data/assets/323051d419ba4e47a4f421fd25e31d5f/model.glb';parent=store.get('323051d419ba4e47a4f421fd25e31d5f')['metadata'];uniform=QA/'B-uniform-real-multiview/result4-conservative';options=json.loads((uniform.parent/'result3/options.json').read_text());paint(source,uniform.parent/'analysis-conservative',uniform,options);export('UniformSemantic',uniform,source,parent);print('CONSERVATIVE_UNIFORM_EXPORT_PASS',flush=True)
# Execute the same real offline SDXL trial with the reviewed protection implementation.
temporary=ROOT/'scripts/verify-semantic-neural-reviewed.py';original=(ROOT/'scripts/verify-semantic-neural.py').read_text();temporary.write_text(original.replace("folder=QA/'neural-completion-real'","folder=QA/'neural-completion-reviewed'"))
run([str(ROOT/'.venv/Scripts/python.exe'),str(temporary)],QA/'neural-reviewed.log');neural=QA/'neural-completion-reviewed';neural_meta=export('NeuralSemantic',neural,source,parent);print('REVIEWED_NEURAL_EXPORT_PASS',flush=True)
# Run an actual second preserve-only edit on that newly generated albedo.
analysis=QA/'license-lineage-analysis';analysis.mkdir(exist_ok=False);options=json.loads((QA/'A-kageyama/analysis/options.json').read_text());view=analysis/'views/front';view.mkdir(parents=True);shutil.copy2(QA/'A-kageyama/analysis/views/front/source.png',view/'source.png');(analysis/'options.json').write_text(json.dumps(options));generated_source=neural/'model.glb'
run([str(ROOT/'.venv-hair/Scripts/python.exe'),str(ROOT/'backend/texture_engine/semantic_cli.py'),'--mode','analysis','--input',str(generated_source),'--output',str(analysis),'--options',str(analysis/'options.json')],analysis/'process.log')
edited=QA/'license-lineage-preserve';options={'provider':'semantic_reference','analysis_id':'a'*32,'front_axis':'negative_y','classes':['hair'],'protected_classes':['skin','face','eyes','mouth','clothes'],'reviewed_alignment':True,'operation':'color_adjust','tint':[1.03,1,1],'completion':'preserve','seam_correction':False};paint(generated_source,analysis,edited,options);lineage=export('LineageSemantic',edited,generated_source,neural_meta)
assert set(lineage['texture_resource_history'])>={'sdxl','mv_adapter'}
assert (edited/'Forge3D_Asset/SDXL_LICENSE.md').is_file() and (edited/'Forge3D_Asset/MV_ADAPTER_LICENSE.txt').is_file()
packages=json.loads((QA/'packages.json').read_text());packages.update({'UniformSemantic':str((uniform/'Forge3D_Asset').relative_to(ROOT)),'NeuralSemantic':str((neural/'Forge3D_Asset').relative_to(ROOT)),'LineageSemantic':str((edited/'Forge3D_Asset').relative_to(ROOT))})
# Complete ancestry for earlier direct-CLI QA packages too, using their actual source metadata.
for name,asset in [('KageSemantic','323051d419ba4e47a4f421fd25e31d5f'),('HinataSemantic','3c2829b70fe046328b86d2a1141736d4')]:
    folder=(ROOT/packages[name]).parent;shutil.copy2(folder/'Forge3D_Asset/asset_manifest.json',folder/'qa-manifest-before-review-lineage.json');report=json.loads((folder/'texture.json').read_text());metadata=texture_metadata(store.get(asset)['metadata'],report,json.loads((folder/'options.json').read_text()),hashlib.sha256((ROOT/'data/assets'/asset/'model.glb').read_bytes()).hexdigest());worker.package({'id':name.lower(),'name':name,'provider':'imported','parent':None,'options':{}},folder,metadata)
(QA/'post-review-packages.json').write_text(json.dumps(packages,indent=2));print('REVIEWED_REAL_COMPOSITION_LINEAGE_EXPORT_PASS',flush=True)
