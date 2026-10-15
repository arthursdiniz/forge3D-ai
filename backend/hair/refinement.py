"""Three bounded guide-width candidates; actual renders, fixed depth/base/roots."""
import copy,json,shutil
from pathlib import Path
import numpy as np
from PIL import Image
from .pipeline import reconstruct_hair
from .metrics import silhouette_metrics,choose_refinement
from backend.texture_engine.region_camera import RegionCamera

def refine_scene(scene,analysis,options,directory,analysis_folder):
    directory=Path(directory);analysis_folder=Path(analysis_folder)
    original=np.asarray(Image.open(analysis_folder/'hair_model_mask.png'))>0;reference=np.asarray(Image.open(analysis_folder/'reference_aligned_mask.png'))>0;classes=np.asarray(Image.open(analysis_folder/'model_classes.png'));protected=np.isin(classes,[2,3,4,5])&~reference
    manual=analysis_folder/'manual_protected_mask.png'
    if manual.is_file():protected|=np.asarray(Image.open(manual))>0
    before=silhouette_metrics(original,reference);results=[];reports=[];measurements=[]
    for index,factor in enumerate([1.,.8,1.2]):
        context=copy.deepcopy(analysis)
        for tip in context['understanding'].get('tips',[]):tip['width']=tip.get('width',.08)*factor
        folder=directory/'local_refinement'/str(index);result,report=reconstruct_hair(scene,context,options,folder)
        if report['status']!='reviewable_candidate':return result,report
        camera=RegionCamera(result,options['front_axis'],1024,analysis['camera_frame']);owners=[i+1 for i,node in enumerate(result.graph.nodes_geometry) if result.graph[node][1] in report['hair_meshes']];generated=np.isin(camera.buffers[2][...,2],owners)&(camera.buffers[0][...,3]>.5)
        measurements.append({'index':index,'width_factor':factor,'occlusion':int((generated&protected).sum()),'metrics':silhouette_metrics(original|generated,reference),'closed_masses':all(m['watertight'] for m in report['integrity']),'protected_geometry':report['protected_geometry']['equivalent']});results.append(result);reports.append(report)
    winner=choose_refinement(measurements,before,max(8,int(protected.sum()*.002)));chosen=0 if winner is None else winner;report=reports[chosen]
    report['local_refinement']={'candidates':measurements,'selected':winner,'scope':'Observed frontal contour diagnostic, subject to face gate, closed 3D masses, fixed cranial support/depth and bounded width changes; no neural identity score.'}
    if winner is None:report.update(retention_required=True,reason='No conservative guide-width candidate passed facial protection and frontal silhouette constraints.')
    for name in ['scalp.glb','hair_isolated.glb']:shutil.copy2(directory/'local_refinement'/str(chosen)/name,directory/name)
    (directory/'hair_geometry.json').write_text(json.dumps(report,indent=2),encoding='utf-8');return results[chosen],report
