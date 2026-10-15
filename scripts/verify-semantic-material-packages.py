"""Repair QA packaging omission using the unchanged production material exporter."""
import json,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];QA=ROOT/'data/semantic-upgrade-20261014';sys.path.insert(0,str(ROOT))
from backend.worker import Worker
worker=Worker(ROOT,None)
for name,relative in json.loads((QA/'packages.json').read_text()).items():
    package=ROOT/relative;folder=package.parent;shutil.copy2(package/'asset_manifest.json',folder/'qa-manifest-before-material-extraction.json')
    with (folder/'delivery-materials.log').open('w') as log:subprocess.run([str(ROOT/'.venv-ai/Scripts/python.exe'),str(ROOT/'backend/texture_engine/export_materials.py'),'--input',str(folder/'model.glb'),'--output',str(package)],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
    report=json.loads((folder/'texture.json').read_text());worker.package({'id':name.lower(),'name':name,'provider':'imported','parent':None,'options':{'pipeline':'URP'}},folder,{'texture':report});print('REAL_MATERIAL_PACKAGING_PASS',name,flush=True)
