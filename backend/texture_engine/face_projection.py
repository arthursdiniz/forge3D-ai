"""Sample original reference pixels on reviewed, front-visible surfaces."""
import numpy as np
from .region_masks import editable_mask,source_coordinates,polygon_mask,rectangle

def project_region(camera,points,normals,rgba,options,owner=None,triangles=None):
    from scipy.ndimage import map_coordinates
    xy=camera.coordinates(points);source=source_coordinates(xy,options);height,width=rgba.shape[:2]
    colors=np.column_stack([map_coordinates(rgba[...,i].astype(float),[source[:,1]*height-.5,source[:,0]*width-.5],order=1,mode='nearest') for i in range(4)])/255
    confidence=camera.visibility(points,normals,owner,triangles)
    allowed=editable_mask(xy,options)&polygon_mask(source,options.get('source_polygon') or rectangle(options['source_box']))
    allowed&=(source.min(axis=1)>=0)&(source.max(axis=1)<1)&(colors[:,3]>=.95)&(confidence>=options.get('minimum_cosine',.75))
    return colors[:,:3],confidence*allowed,xy,source
