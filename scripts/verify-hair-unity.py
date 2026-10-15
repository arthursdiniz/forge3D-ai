"""Fresh Unity project; import original/candidate through the actual packaged exporter."""
import json,shutil,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];QA=ROOT/'data/hair-upgrade-20261013';data=json.loads((QA/'live-delivery-final.json').read_text());project=ROOT/'data/UnityHairValidation'
assert not project.exists(),'Preserve existing QA; choose another fresh directory if repeated.'
(project/'Assets/Editor').mkdir(parents=True)
for name in ['Packages','ProjectSettings']:shutil.copytree(ROOT/'data/UnityTextureFidelityValidation'/name,project/name)
for name,job in data['exports'].items():shutil.copytree(ROOT/'data/assets'/job['id']/'Forge3D_Asset',project/'Assets'/name)
for source in ['unity/Forge3DImporter.cs','tests/UnityHairValidation.cs']:shutil.copy2(ROOT/source,project/'Assets/Editor'/Path(source).name)
subprocess.run(['C:/Program Files/Unity/Hub/Editor/6000.3.0f1/Editor/Unity.exe','-batchmode','-nographics','-projectPath',str(project),'-executeMethod','UnityHairValidation.BatchValidate','-logFile',str(project/'hair-validation.log')],check=True,timeout=300)
reports={f'{name}_{pipeline}':json.loads((project/'Assets'/name/f'unity_{pipeline}.json').read_text()) for name in data['exports'] for pipeline in ['urp','builtin']}
assert all(r['passed'] for r in reports.values());(QA/'unity-validation.json').write_text(json.dumps({'passed':True,'scope':'Actual Unity6000.3 import; original world vertices/orientation, UV/normals within1e-5, material slots, scale/up-axis, albedo color space, URP/Built-in. Static prefab; no gameplay/rig claim.','reports':reports},indent=2),encoding='utf-8');print('HAIR_REAL_UNITY_URP_BUILTIN_PASS',flush=True)
