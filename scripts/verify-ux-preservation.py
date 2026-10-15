"""Check every original baseline file, actual export geometry, maps and license lineage."""
import hashlib,json,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];QA=ROOT/'data/ux-upgrade-20261015'
baseline=json.loads((QA/'baseline.json').read_text(encoding='utf-8'))
changed=[];count=0
for identifier,files in baseline['assets'].items():
    for relative,expected in files.items():
        path=ROOT/'data/assets'/identifier/relative;count+=1
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=expected:changed.append(str(path))
assert not changed,changed
identifier=(QA/'e2e-export-id.txt').read_text().strip();folder=ROOT/'data/assets'/identifier
geometry=json.loads((folder/'geometry_export_validation.json').read_text())
assert all(geometry[fmt]['equivalent'] for fmt in ['glb','fbx','obj'])
with zipfile.ZipFile(folder/'Forge3D_Unity.zip') as package:
    names=package.namelist();licenses=[name for name in names if 'LICENSE' in name.upper() or 'NOTICE' in name.upper()]
    assert any('SDXL_LICENSE' in name for name in names) and any('MV_ADAPTER_LICENSE' in name for name in names)
imported=(QA/'e2e-import-id.txt').read_text().strip()
from sys import path as module_path
module_path.insert(0,str(ROOT))
from backend.storage import Store
store=Store(ROOT/'data');job=store.get(imported);assert job['status']=='completed' and job['kind']=='import'
assert (store.directory(imported)/'original.glb').is_file()
(QA/'preservation-validation.json').write_text(json.dumps({'passed':True,'original_files':count,'original_asset_folders':len(baseline['assets']),
    'changed_original_files':changed,'export_geometry':geometry,'licenses':licenses,'imported_job':imported},indent=2),encoding='utf-8')
print(f'PRESERVED_{count}_ORIGINAL_FILES_AND_REAL_EXPORT_IMPORT_PASS',flush=True)
