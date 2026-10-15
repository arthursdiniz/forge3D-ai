"""Reviewed categorical transfer on actual visible owner/primitive surfaces."""
import numpy as np
from .region_masks import source_coordinates,editable_mask

def sample_labels(labels,xy):
    from scipy.ndimage import map_coordinates
    h,w=labels.shape
    return map_coordinates(np.asarray(labels),[xy[:,1]*h-.5,xy[:,0]*w-.5],order=0,mode='constant',cval=0).astype('u1')

def semantic_allowed(source,target,accept_unknown=False):
    source=np.asarray(source);target=np.asarray(target);same=(source==target)|(np.isin(source,[2,3])&np.isin(target,[2,3]))
    return (source>1)&(same|((target==0)&bool(accept_unknown)))

def project_semantic(camera,points,normals,rgba,source_labels,target_labels,registration,owner=None,triangles=None,source_origin=None,gradient_map=None):
    from scipy.ndimage import map_coordinates
    from .texture_fusion import gradient_reference
    xy=camera.coordinates(points);source_xy=source_coordinates(xy,registration);h,w=rgba.shape[:2];coordinates=[source_xy[:,1]*h-.5,source_xy[:,0]*w-.5]
    rgb=np.column_stack([map_coordinates(rgba[...,i].astype(float),coordinates,order=1,mode='nearest') for i in range(3)])/255
    source=sample_labels(source_labels,source_xy);target=sample_labels(target_labels,xy);alpha=map_coordinates(rgba[...,3].astype(float),coordinates,order=0,mode='constant',cval=0)/255
    gradient_map=gradient_reference(rgba)[...,0].astype(float)/255 if gradient_map is None else gradient_map
    gradient=map_coordinates(gradient_map,coordinates,order=0,mode='constant',cval=0)
    edges=gradient>.04
    if edges.any():rgb[edges]=np.column_stack([map_coordinates(rgba[...,i].astype(float),[coordinate[edges] for coordinate in coordinates],order=0,mode='nearest') for i in range(3)])/255
    region=editable_mask(xy,registration);potential=(source>1)|(target>1)|~region;visibility=np.zeros(len(points))
    if potential.any():visibility[potential]=camera.visibility(points[potential],normals[potential],owner,triangles[potential] if triangles is not None else None)
    allowed=semantic_allowed(source,target,registration.get('accept_unknown_target',False));inside=(source_xy.min(axis=1)>=0)&(source_xy.max(axis=1)<1);legal=(visibility>=registration.get('minimum_cosine',.65))&(alpha>=.95)&inside&region
    origin=sample_labels(source_origin,source_xy) if source_origin is not None else np.where(source>0,1,0).astype('u1')
    return {'rgb':rgb,'weight':visibility*legal*allowed,'source_class':source,'target_class':target,'origin':origin,'source_xy':source_xy,'target_xy':xy,'gradient':gradient,'conflict':legal&~allowed&(source>1)&(target>0),'visible':legal,'target_visible':visibility>0,'unknown_target':legal&(target==0),'protected':(visibility>0)&~region}
