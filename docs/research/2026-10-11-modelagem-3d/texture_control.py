"""Additional SR control: both pipelines MC256 and texture1024, same input."""
import importlib.util,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('driver',HERE/'run_experiments.py')
driver=importlib.util.module_from_spec(spec);spec.loader.exec_module(driver)
dest=driver.OUT/'runs/sr_three_quarter_vertex1024'
options={'quality':'fast','texture_resolution':1024,'background_mode':'preserve_alpha','foreground_ratio':.85,'preparation_preset':'prop'}
driver.write(dest/'options.json',options)
if not (dest/'inference.json').exists():
    driver.execute([driver.INSTALL/'.venv-ai/Scripts/python.exe',HERE/'run_experiments.py','--child','--provider','triposr','--image',driver.OUT/'fixture/three_quarter.png','--output',dest,'--options',dest/'options.json','--vertex-ablation'],dest)
if not (dest/'model.glb').exists():
    driver.pipeline(dest/'original.glb',dest,'prepare',{'raw_up':'Z','geometry_only':False,'front_axis':'x','texture_resolution':1024})
original=driver.OUT/'runs/sr_three_quarter_neural'
import numpy as np,trimesh
a=trimesh.load(original/'original.glb',force='mesh',process=False)
b=trimesh.load(dest/'original.glb',force='mesh',process=False)
report={'same_reference':True,'mc_resolution_both':256,'texture_resolution_both':1024,'vertices_identical':bool(np.array_equal(a.vertices,b.vertices)),'faces_identical':bool(np.array_equal(a.faces,b.faces)),'vertex_colors_identical':bool(np.array_equal(a.visual.vertex_colors,b.visual.vertex_colors)),'geometry_changed_by_texture_method':not(np.array_equal(a.vertices,b.vertices) and np.array_equal(a.faces,b.faces)),'comparison_scope':'controlled pipelines with equal geometry and atlas resolution; UV layouts differ; no subjective texture score inferred','inference':json.loads((dest/'inference.json').read_text())}
driver.write(driver.OUT/'texture_control.json',report)
driver.pipeline(dest/'model.glb',driver.OUT/'exports/sr_three_quarter_vertex1024','export',{})
package=driver.OUT/'exports/sr_three_quarter_vertex1024/Forge3D_Asset'
editor=package/'Editor';editor.mkdir(exist_ok=True)
editor_class='Forge3DResearch_sr_three_quarter_vertex1024'
script=(driver.ROOT/'unity/Forge3DImporter.cs').read_text(encoding='utf-8').replace('Forge3DImporter',editor_class).replace('Tools/Forge3D/Import selected asset package','Tools/Forge3DResearch/sr_three_quarter_vertex1024')
(editor/(editor_class+'.cs')).write_text(script,encoding='utf-8')
texture=next((package/'Textures').glob('*.png'))
driver.write(package/'asset_manifest.json',{'name':'sr_three_quarter_vertex1024','editor_class':editor_class,'pipeline':'URP','model':'Models/Model.fbx','albedo':'Textures/'+texture.name,'fbx_validation':json.loads((driver.OUT/'exports/sr_three_quarter_vertex1024/fbx_validation.json').read_text())})
print('TEXTURE_CONTROL_COMPLETE '+json.dumps({k:v for k,v in report.items() if k!='inference'}),flush=True)
