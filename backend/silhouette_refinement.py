"""Bounded lateral deformation using a single reference, not multiview AI."""
import numpy as np
from .reference_texture import projection_frame,image_coordinates,rasterize_front

def runs(row):
    padded=np.pad(np.asarray(row,dtype=np.int8),(1,1))
    edges=np.diff(padded)
    pairs=list(zip(np.flatnonzero(edges==1),np.flatnonzero(edges==-1)))
    return [(start,end) for start,end in pairs if end-start>=2]

def refine_silhouette(vertices,faces,rgba,strength=0.65,max_displacement_ratio=0.03,resolution=512):
    from PIL import Image
    from scipy.ndimage import gaussian_filter,map_coordinates
    v=np.asarray(vertices,dtype=np.float64);f=np.asarray(faces)
    if not 0<=strength<=1 or not 0<=max_displacement_ratio<=0.03:raise ValueError('Refinement limits exceeded.')
    frame=projection_frame(v,rgba)
    front=rasterize_front(v,f,frame,resolution)
    source=front[::-1,:,3]>0.5
    target=np.asarray(Image.fromarray(rgba[...,3]).resize((resolution,resolution),Image.Resampling.NEAREST))>128
    before=np.count_nonzero(source&target)/max(np.count_nonzero(source|target),1)
    field=np.zeros((resolution,resolution),float);weights=np.zeros_like(field);blocked=np.zeros(resolution,bool);matched=0
    for row in range(resolution):
        old=runs(source[row]);new=runs(target[row])
        if not old or len(old)!=len(new):
            blocked[row]=bool(old and new)
            continue
        if any(not 0.6<=(b-a)/max(y-x,1)<=1.7 for (x,y),(a,b) in zip(old,new)):continue
        anchors=np.array([edge for pair in old for edge in pair],float)
        desired=np.array([edge for pair in new for edge in pair],float)
        field[row]=np.interp(np.arange(resolution)+0.5,anchors,desired-anchors)
        weights[row]=1
        matched+=1
    # Smooth displacement rather than geometry; depth/Y and connectivity remain.
    field=gaussian_filter(field,sigma=(3,2),mode='nearest')/np.maximum(gaussian_filter(weights,sigma=(3,2),mode='nearest'),1e-8)
    field[blocked]=0
    coords=image_coordinates(v,frame)*resolution/np.array([frame['width'],frame['height']])
    delta=map_coordinates(field,[coords[:,1]-0.5,coords[:,0]-0.5],order=1,mode='nearest')
    delta*=frame['width']/resolution/frame['scale']*strength
    maximum=float(np.ptp(v[:,1]))*max_displacement_ratio
    delta=np.clip(delta,-maximum,maximum)
    output=v.copy();output[:,0]+=delta
    after_mask=rasterize_front(output,f,frame,resolution)[::-1,:,3]>0.5
    after=np.count_nonzero(after_mask&target)/max(np.count_nonzero(after_mask|target),1)
    accepted=after>before+1e-6
    if not accepted:output=v.copy();delta[:]=0;after=before
    return output,{'method':'bounded_reference_silhouette','accepted':bool(accepted),'silhouette_iou_before':round(float(before),6),'silhouette_iou_after':round(float(after),6),'metric_scope':'2D foreground overlap in estimated orthographic front camera; not perceptual fidelity or hidden-geometry accuracy','matched_scanlines':matched,'strength':strength,'max_displacement_ratio':max_displacement_ratio,'actual_max_displacement':float(np.abs(delta).max()),'faces_changed':0,'depth_changed':False,'height_changed':False,'reference_frame':frame,'view_assumption':'canonicalY-up, front+Z, reference same pose; single-view constraint'}
