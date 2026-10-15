"""Reviewed 2D ownership and alignment; labels alone never imply semantics."""
import numpy as np

def polygon_mask(points,polygon):
    points=np.asarray(points);polygon=np.asarray(polygon,dtype=float)
    if polygon.ndim!=2 or polygon.shape[1]!=2 or not 3<=len(polygon)<=64 or not np.isfinite(polygon).all() or polygon.min()<0 or polygon.max()>1:raise ValueError('Invalid normalized polygon.')
    x,y=points.T;inside=np.zeros(len(points),bool)
    for a,b in zip(polygon,np.roll(polygon,-1,axis=0)):
        crossing=(a[1]>y)!=(b[1]>y)
        limit=(b[0]-a[0])*(y-a[1])/(b[1]-a[1]+1e-30)+a[0]
        inside^=crossing&(x<limit)
    return inside

def rectangle(box):
    l,t,r,b=box;return [[l,t],[r,t],[r,b],[l,b]]

def editable_mask(points,options):
    selected=polygon_mask(points,options.get('target_polygon') or rectangle(options['target_box']))
    for protected in options.get('protected',[]):selected&=~polygon_mask(points,protected)
    return selected

def source_coordinates(points,options):
    points=np.asarray(points)
    if options.get('source_points') or options.get('target_points'):
        source=np.asarray(options.get('source_points',[]),dtype=float);target=np.asarray(options.get('target_points',[]),dtype=float)
        if source.shape!=target.shape or source.ndim!=2 or source.shape[1]!=2 or not 3<=len(source)<=28 or not np.isfinite(source).all() or not np.isfinite(target).all():raise ValueError('Provide 3–28 paired finite landmarks.')
        design=np.column_stack([target,np.ones(len(target))])
        if np.linalg.matrix_rank(design)<3:raise ValueError('Alignment points are collinear; review alignment.')
        transform=np.linalg.lstsq(design,source,rcond=None)[0]
        if np.linalg.det(transform[:2])<=0:raise ValueError('Mirrored or singular alignment is not allowed.')
        return np.column_stack([points,np.ones(len(points))])@transform
    source=np.asarray(options['source_box']);target=np.asarray(options['target_box'])
    if source.shape!=(4,) or target.shape!=(4,) or not np.isfinite(source).all() or not np.isfinite(target).all() or np.any(source[2:]<=source[:2]) or np.any(target[2:]<=target[:2]):raise ValueError('Invalid reference/model rectangles.')
    return source[:2]+(points-target[:2])/(target[2:]-target[:2])*(source[2:]-source[:2])
