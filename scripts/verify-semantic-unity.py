"""Actual import of five newly packaged semantic variants in a fresh Unity project."""
import json,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];QA=ROOT/'data/semantic-upgrade-20261014';reviewed='--reviewed' in sys.argv;project=ROOT/'data'/('UnitySemanticValidationReviewed' if reviewed else 'UnitySemanticValidationFinal' if '--final' in sys.argv else 'UnitySemanticValidation')
assert not project.exists(),'Choose a fresh directory; previous QA is immutable.'
(project/'Assets/Editor').mkdir(parents=True)
for name in ['Packages','ProjectSettings']:shutil.copytree(ROOT/'data/UnityTextureFidelityValidation'/name,project/name)
packages=json.loads((QA/('post-review-packages.json' if reviewed else 'packages.json')).read_text())
for name,folder in packages.items():shutil.copytree(ROOT/folder,project/'Assets'/name)
for source in ['unity/Forge3DImporter.cs','tests/UnitySemanticValidation.cs']:shutil.copy2(ROOT/source,project/'Assets/Editor'/Path(source).name)
subprocess.run(['C:/Program Files/Unity/Hub/Editor/6000.3.0f1/Editor/Unity.exe','-batchmode','-nographics','-projectPath',str(project),'-executeMethod','UnitySemanticValidation.BatchValidate','-logFile',str(project/'semantic-validation.log')],check=True,timeout=300)
reports={f'{name}_{pipeline}':json.loads((project/'Assets'/name/f'unity_{pipeline}.json').read_text()) for name in packages for pipeline in ['urp','builtin']}
assert all(r['passed'] for r in reports.values())
(QA/('unity-reviewed-validation.json' if reviewed else 'unity-validation.json')).write_text(json.dumps({'passed':True,'scope':'Actual Unity6000.3 import of packaged assets; finite mesh/UV/normals, topology/material slots, albedo/data-map color space, URP/Built-in. Static prefab only. Three-format world-geometry equality validated separately.','reports':reports},indent=2),encoding='utf-8')
print('SEMANTIC_REAL_UNITY_PASS',flush=True)
