"""Non-product postprocessing ablations and export of selected research meshes."""
import importlib.util
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('research_driver', HERE/'run_experiments.py')
driver=importlib.util.module_from_spec(spec)
spec.loader.exec_module(driver)
OUT=driver.OUT

def main():
    scores=json.loads((OUT/'geometry_metrics.json').read_text())
    sg=[s for s in scores if s['name'].startswith('sg_')]
    best=min(sg,key=lambda s:s['normalized_surface_distance_percent'])
    selection={'selection':'oracle on this single known chair: surface distance, not deployable automatic ranking', 'selected_run':best['name']}
    driver.write(OUT/'selection.json',selection)
    for label,ratio in [('medium',.1),('low',.02)]:
        dest=OUT/'optimized'/('sg_best_'+label)
        if not (dest/'model.glb').exists():
            driver.pipeline(best['model'],dest,'transform',{'operation':'decimate','ratio':ratio})
        print('DECIMATION_READY '+label,flush=True)
    quality=OUT/'runs/sg_front_quality512'
    refined=OUT/'optimized/sg_quality_refined'
    driver.write(refined/'options.json',{'operation':'refine_silhouette'})
    if not (refined/'model.glb').exists():
        driver.execute([driver.INSTALL/'.venv-ai/Scripts/python.exe',driver.ROOT/'backend/refine_mesh.py','--input',quality/'model.glb','--output',refined,'--options',refined/'options.json','--source',OUT/'fixture/front.png','--generation-options',quality/'options.json'],refined)
    exports=[(best['name'],Path(best['model'])),('sg_best_medium',OUT/'optimized/sg_best_medium/model.glb'),('sg_best_low',OUT/'optimized/sg_best_low/model.glb'),('sr_three_quarter_neural',OUT/'runs/sr_three_quarter_neural/model.glb'),('sr_three_quarter_vertex',OUT/'runs/sr_three_quarter_vertex/model.glb')]
    for name,source in exports:
        if not source.exists():
            print('SOURCE_NOT_READY '+name,flush=True)
            continue
        dest=OUT/'exports'/name
        if not (dest/'fbx_validation.json').exists():
            driver.pipeline(source,dest,'export',{})
        package=dest/'Forge3D_Asset'
        editor_class='Forge3DResearch_'+name
        editor=package/'Editor';editor.mkdir(exist_ok=True)
        script=(driver.ROOT/'unity/Forge3DImporter.cs').read_text(encoding='utf-8').replace('Forge3DImporter',editor_class).replace('Tools/Forge3D/Import selected asset package','Tools/Forge3DResearch/'+name)
        (editor/(editor_class+'.cs')).write_text(script,encoding='utf-8')
        textures=sorted((package/'Textures').glob('*.png'))
        driver.write(package/'asset_manifest.json',{'name':name,'editor_class':editor_class,'pipeline':'URP','model':'Models/Model.fbx','albedo':'Textures/'+textures[0].name if textures else None,'fbx_validation':json.loads((dest/'fbx_validation.json').read_text())})
        print('FBX_EXPORT_READY '+name,flush=True)
    driver.write(OUT/'exports.json',[{'name':name,'package':str(OUT/'exports'/name/'Forge3D_Asset'),'validation':json.loads((OUT/'exports'/name/'fbx_validation.json').read_text())} for name,source in exports if (OUT/'exports'/name/'fbx_validation.json').exists()])
    print('POSTPROCESS_AND_FBX_COMPLETE',flush=True)

if __name__=='__main__':main()
