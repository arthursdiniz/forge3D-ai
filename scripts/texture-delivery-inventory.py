"""Hash the local delivery and independently recheck all audited original assets."""
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];qa=ROOT/'data/texture-engine-20261012'
def digest(path):
    value=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(8*1024*1024),b''):value.update(chunk)
    return value.hexdigest()
baseline=json.loads((qa/'baseline.json').read_text())
changes=[]
for path,record in baseline['source'].items():
    current=digest(ROOT/path)
    changes.append({'path':path,'before_sha256':record['sha256'],'current_sha256':current,'changed':current!=record['sha256']})
preservation={'checked_files':0,'changed_files':[]}
for identifier,files in baseline['assets'].items():
    for name,expected in files.items():
        path=ROOT/'data/assets'/identifier/name;preservation['checked_files']+=1
        if not path.is_file() or digest(path)!=expected:preservation['changed_files'].append(str(path.relative_to(ROOT)))
assert not preservation['changed_files'],preservation
preservation['all_originals_preserved']=True
(qa/'preservation-final.json').write_text(json.dumps(preservation,indent=2),encoding='utf-8')
components=set(ROOT/path for path in baseline['source'])
for pattern in ['backend/texture_engine/*.py','scripts/*texture*.py','scripts/*texture*.ps1','tests/*texture*.py','tests/UnityTextureValidation.cs']:
    components.update(ROOT.glob(pattern))
components.update(ROOT/path for path in ['blender/import_static.py','backend/inference_v2.py','frontend/src/TextureWorkspace.tsx','frontend/src/generationOptions.ts','docs/TEXTURE_ENGINE.md','docs/superpowers/plans/2026-10-12-texture-engine.md','docs/superpowers/specs/2026-10-12-texture-engine-design.md','Setup-TextureEngine.bat','README.md'])
files=[{'path':str(path.relative_to(ROOT)).replace('\\','/'),'bytes':path.stat().st_size,'sha256':digest(path)} for path in sorted(components) if path.is_file()]
resources=[]
for name in ['sdxl','adapter']:
    path=ROOT/'models/texture'/name/'download_manifest.json';manifest=json.loads(path.read_text())
    resources.append({'manifest':str(path.relative_to(ROOT)),'sha256':digest(path),'repo':manifest.get('repo'),'revision':manifest.get('revision'),'license':manifest.get('license'),'bytes':sum(record['bytes'] for record in manifest['files']),'files':len(manifest['files'])})
evidence=[]
for name in ['full-suite-final.log','final-regressions-red.log','final-regressions-green.log','final-review.md','delivery-texture-result.json','delivery-hinata-result.json','final-object-export.json','geometry-only-live-result.json','geometry-only-live-export-result.json','import-formats-final/result.json','live-flow.json','diagnostics-final/before-after.png','diagnostics-final/all-views.png','ui-desktop-delivery.png','ui-mobile-delivery.png','preservation-final.json']:
    path=qa/name
    if path.is_file():evidence.append({'path':str(path.relative_to(ROOT)),'sha256':digest(path)})
for path in (ROOT/'data/UnityTextureFinalValidation/Assets/Forge3D_Asset').glob('unity_texture_*.json'):
    report=json.loads(path.read_text());assert report['passed'] and report['materials']==2
    evidence.append({'path':str(path.relative_to(ROOT)),'sha256':digest(path)})
inventory={'scope':'Local workspace delivery; no Git metadata. Additional file hashes are current inventory, not inferred baseline additions.','audited_source_changes':changes,'implementation_files':files,'resources':resources,'evidence':evidence,'preservation':preservation,'automated_tests':{'passed':163,'warning':'Existing Starlette/anyio deprecation'},'review':'Fresh independent review completed; four Important plus regraded metrics fixed in one RED/GREEN pass; global footer metric source Minor deferred.'}
(qa/'delivery-inventory.json').write_text(json.dumps(inventory,indent=2),encoding='utf-8')
print(f'DELIVERY_INVENTORY_PASS {len(files)} files; {preservation["checked_files"]} originals unchanged')
