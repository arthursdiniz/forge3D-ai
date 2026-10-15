"""Class-aware multiview fusion and bounded real-surface propagation."""
import numpy as np
from .texture_fusion import fuse_observations

def fuse_semantic(colors,weights,gradients,classes):
    weights=np.asarray(weights).copy();classes=np.asarray(classes);winner=np.argmax(weights,axis=1);rows=np.arange(len(weights));selected_class=classes[rows,winner];known=weights>0;conflict=(known&(classes!=selected_class[:,None])).any(axis=1)
    weights[classes!=selected_class[:,None]]=0
    report=fuse_observations(colors,weights,gradients,'robust');report['class']=np.where(report['confidence']>0,selected_class,0).astype('u1');report['semantic_conflict']=conflict
    return report

def surface_fill(positions,normals,colors,observed,classes,components,max_distance):
    from scipy.spatial import cKDTree
    result=np.asarray(colors).copy();filled=np.zeros(len(result),bool);classes=np.asarray(classes);components=np.asarray(components)
    for label in np.unique(classes):
        if label<=1:continue
        for component in np.unique(components[classes==label]):
            group=(classes==label)&(components==component);seeds=np.flatnonzero(group&observed);holes=np.flatnonzero(group&~observed)
            if not len(seeds) or not len(holes):continue
            distance,index=cKDTree(positions[seeds]).query(positions[holes],k=1);source=seeds[index];dot=np.sum(normals[holes]*normals[source],axis=1);valid=(distance<=max_distance)&(dot>.95);selected=holes[valid];result[selected]=colors[source[valid]];filled[selected]=True
    return result,filled

def semantic_seams(mesh,image,editable,classes):
    from .texture_seams import correct_seams
    result=image.copy()
    for label in np.unique(classes):
        if label>1:result=correct_seams(mesh,result,editable&(classes==label))
    return result
