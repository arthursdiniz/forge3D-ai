"""Conservative observation fusion: confidence never changes observed RGB."""
import numpy as np
from ..reference_texture import NEUTRAL

def srgb_to_linear(values):
    values=np.asarray(values);return np.where(values<=.04045,values/12.92,((values+.055)/1.055)**2.4)

def linear_to_srgb(values):
    values=np.maximum(values,0);return np.where(values<=.0031308,values*12.92,1.055*values**(1/2.4)-.055)

def fuse_observations(colors,weights,gradients,mode='robust'):
    colors=np.asarray(colors);weights=np.asarray(weights);gradients=np.asarray(gradients)
    if mode not in ['winner','robust']:raise ValueError('Unknown fusion mode.')
    if colors.ndim!=3 or colors.shape[2]!=3 or weights.shape!=colors.shape[:2] or gradients.shape!=weights.shape:raise ValueError('Invalid observation shapes.')
    if not all(np.isfinite(v).all() for v in [colors,weights,gradients]):raise ValueError('Nonfinite observations.')
    rows=np.arange(len(colors));winner=np.argmax(weights,axis=1);confidence=weights[rows,winner];rgb=colors[rows,winner].copy()
    visible=weights>0;compatible=np.max(np.abs(colors-rgb[:,None,:]),axis=2)<=.08
    safe=(gradients<.04)&(gradients[rows,winner,None]<.04)&compatible&visible&(weights>=confidence[:,None]*.35)
    safe[rows,winner]=visible[rows,winner]
    mixed=(safe.sum(axis=1)>1)&(mode=='robust')
    if mixed.any():
        selected=weights[mixed]*safe[mixed]
        rgb[mixed]=linear_to_srgb((srgb_to_linear(colors[mixed])*selected[...,None]).sum(axis=1)/selected.sum(axis=1)[:,None])
    contributors=np.left_shift(np.uint8(1),np.arange(colors.shape[1],dtype='u1'))
    bits=np.sum(safe*contributors,axis=1).astype('u1')
    bits[~mixed]=np.left_shift(np.uint8(1),winner[~mixed].astype('u1'))
    unknown=confidence<=0;rgb[unknown]=NEUTRAL;bits[unknown]=0
    return {'rgb':rgb,'confidence':confidence,'source_view':np.where(unknown,0,winner+1).astype('u1'),'mixed':mixed,'conflict':(visible&~compatible).any(axis=1),'contributors':bits}

def gradient_reference(rgba):
    """Local edges protect facial/clothing features from cross-view averaging."""
    from scipy.ndimage import maximum_filter
    rgb=np.asarray(rgba)[...,:3].astype('f4')/255
    gx=np.max(np.abs(np.diff(rgb,axis=1,prepend=rgb[:,:1])),axis=2)
    gy=np.max(np.abs(np.diff(rgb,axis=0,prepend=rgb[:1])),axis=2)
    gradient=maximum_filter(np.maximum(gx,gy),size=3)
    return np.dstack([np.repeat(gradient[...,None],3,axis=2)*255,np.asarray(rgba)[...,3]]).clip(0,255).astype('u1')
