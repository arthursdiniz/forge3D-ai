"""Import the actual one-action texture export in fresh Unity, both render pipelines."""
import json
import shutil
import subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];QA=ROOT/'data/ux-upgrade-20261015'
identifier=(QA/'e2e-export-id.txt').read_text().strip();package=ROOT/'data/assets'/identifier/'Forge3D_Asset'
project=QA/'UnityStudioValidation';assert not project.exists(),'Retain earlier validation projects.'
(project/'Assets/Editor').mkdir(parents=True)
for name in ['Packages','ProjectSettings']:
    shutil.copytree(ROOT/'data/UnityTextureFidelityValidation'/name,project/name)
shutil.copytree(package,project/'Assets/StudioAsset')
shutil.copy2(ROOT/'unity/Forge3DImporter.cs',project/'Assets/Editor/Forge3DImporter.cs')
source=(ROOT/'tests/UnitySemanticValidation.cs').read_text()
source=source.replace('UnitySemanticValidation','UnityStudioValidation').replace('new[]{"KageSemantic","HinataSemantic","StylizedSemantic","UniformSemantic","NeuralSemantic","LineageSemantic"}','new[]{"StudioAsset"}')
(project/'Assets/Editor/UnityStudioValidation.cs').write_text(source,encoding='utf-8')
subprocess.run(['C:/Program Files/Unity/Hub/Editor/6000.3.0f1/Editor/Unity.exe','-batchmode','-nographics','-projectPath',str(project),
                '-executeMethod','UnityStudioValidation.BatchValidate','-logFile',str(project/'studio-validation.log')],check=True,timeout=300)
reports={name:json.loads((project/'Assets/StudioAsset'/f'unity_{name}.json').read_text()) for name in ['urp','builtin']}
assert all(r['passed'] for r in reports.values())
(QA/'unity-validation.json').write_text(json.dumps({'passed':True,'export_job':identifier,'reports':reports,
    'scope':'Actual Unity6000.3 static prefab, finite vertices/UV/normals, material slots, albedo color space, URP and Built-in. Not animation or gameplay testing.'},indent=2),encoding='utf-8')
print('STUDIO_REAL_UNITY_URP_BUILTIN_PASS',flush=True)
