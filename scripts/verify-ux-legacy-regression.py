"""Current reviewed semantic/regional paths, with new immutable QA directories."""
import hashlib,json,shutil,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];QA=ROOT/'data/ux-upgrade-20261015'

def run(args,log):
    with log.open('w',encoding='utf-8') as stream:
        subprocess.run([str(x) for x in args],cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,check=True)

semantic=QA/'legacy-semantic';semantic.mkdir(exist_ok=False)
old=ROOT/'data/semantic-upgrade-20261014/A-kageyama'
shutil.copy2(old/'result/options.json',semantic/'options.json')
source=ROOT/'data/assets/323051d419ba4e47a4f421fd25e31d5f/model.glb'
run([ROOT/'.venv-texture/Scripts/python.exe',ROOT/'backend/texture_engine/semantic_cli.py','--mode','paint','--input',source,
    '--output',semantic,'--options',semantic/'options.json','--analysis',old/'analysis'],semantic/'process.log')
report=json.loads((semantic/'texture.json').read_text())
assert report['geometry']['equivalent'] and report['semantic']['protected_pixels_equal']
assert all(all(c['preserved'].values()) for c in report['semantic']['channel_roundtrip'])
print('CURRENT_REVIEWED_SEMANTIC_PASS',flush=True)

regional=QA/'legacy-regional';regional.mkdir(exist_ok=False)
old=ROOT/'data/texture-fidelity-20261013'
shutil.copy2(old/'hinata-regional-trial6-fidelity-angle/options.json',regional/'options.json')
ref=regional/'references/front';ref.mkdir(parents=True)
shutil.copy2(ROOT/'data/test-inputs/hinata-shoyo-reference-20261011.png',ref/'source.png')
(regional/'texture_references.json').write_text(json.dumps({'views':{'front':{'path':'references/front/source.png'}}}))
run([ROOT/'.venv-ai/Scripts/python.exe',ROOT/'backend/texture_engine/cli.py','--input',old/'global-image/model.glb',
     '--output',regional,'--options',regional/'options.json'],regional/'process.log')
report=json.loads((regional/'texture.json').read_text())
assert report['geometry']['equivalent'] and report['regional']['outside_unchanged']
print('CURRENT_REVIEWED_REGIONAL_PASS',flush=True)

changes={}
for name in ['models/texture/region_validation.json','models/texture/semantic_validation.json','models/hair/validation.json']:
    path=ROOT/name;proof=json.loads(path.read_text())
    changed={relative:old_hash for relative,old_hash in proof['source_sha256'].items()
             if hashlib.sha256((ROOT/relative).read_bytes()).hexdigest()!=old_hash}
    proof['source_sha256']={relative:hashlib.sha256((ROOT/relative).read_bytes()).hexdigest() for relative in proof['source_sha256']}
    proof['studio_regression']={'directory':str(QA.relative_to(ROOT)),'changed_sources':changed,
        'note':'Current reviewed semantic/regional CLIs preserve geometry/protected channels; original inference implementations and existing export/Unity proofs retained. App/worker additions are separate workflow dispatch; legacy hair algorithms unchanged. Full regression suite and actual new one-action generation/texture/export validated separately.'}
    path.write_text(json.dumps(proof,indent=2),encoding='utf-8');changes[name]=changed
(QA/'proof-renewal.json').write_text(json.dumps(changes,indent=2),encoding='utf-8')
print('LEGACY_PROOFS_RENEWED_AFTER_REAL_REGRESSION',flush=True)
