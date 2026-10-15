"""Categorical masks, intrinsic-coordinate manual editing and observed features."""
import numpy as np
from PIL import Image,ImageDraw
from .semantic_taxonomy import CLASS_NAMES,NATIVE_MAPPING

PALETTE=np.array([[80,80,80],[0,0,0],[255,210,170],[90,150,255],[240,65,70],[50,230,220],[255,70,180],[155,80,230],[160,200,60],[230,145,50],[220,120,80],[180,160,125],[210,160,130],[195,155,130],[240,180,150],[215,165,140],[140,90,240],[80,105,225],[175,125,220],[180,190,205],[70,110,160],[220,185,70],[130,205,135],[200,150,185],[245,245,245]],dtype='u1')

def map_native(native,crop,alpha):
    native=np.asarray(native);alpha=np.asarray(alpha)
    if native.shape!=alpha.shape:raise ValueError('Semantic dimensions differ from reference.')
    result=np.zeros(native.shape,'u1');h,w=result.shape;l,t,r,b=crop
    inside=np.zeros(native.shape,bool);inside[int(t*h):int(np.ceil(b*h)),int(l*w):int(np.ceil(r*w))]=True
    for label,common in NATIVE_MAPPING.items():result[(native==label)&inside]=common
    result[alpha<=128]=1
    return result

def apply_strokes(learned,strokes,initial_labels=None,initial_origin=None):
    original=np.asarray(learned);labels=original.copy() if initial_labels is None else np.asarray(initial_labels).copy();origin=np.where(original>0,1,0).astype('u1') if initial_origin is None else np.asarray(initial_origin).copy();h,w=labels.shape
    for stroke in strokes:
        mask=Image.new('L',(w,h));draw=ImageDraw.Draw(mask);radius=max(1,int(round(stroke['radius']*min(w,h))));points=[(min(w-1,round(p[0]*w)),min(h-1,round(p[1]*h))) for p in stroke['points']]
        if len(points)>1:draw.line(points,fill=255,width=radius*2+1)
        for x,y in points:draw.ellipse((x-radius,y-radius,x+radius,y+radius),fill=255)
        selected=np.asarray(mask)>0;operation=stroke.get('operation','paint')
        if operation=='restore':labels[selected]=original[selected];origin[selected]=np.where(original[selected]>0,1,0)
        else:labels[selected]=0 if operation=='erase' else stroke['label'];origin[selected]=2
    return labels,origin

def apply_polygons(labels,origin,polygons):
    from .region_masks import polygon_mask
    labels=np.asarray(labels).copy();origin=np.asarray(origin).copy();h,w=labels.shape;rows,cols=np.indices(labels.shape);xy=np.column_stack([(cols.ravel()+.5)/w,(rows.ravel()+.5)/h])
    for region in polygons:
        mask=polygon_mask(xy,region['points']).reshape(labels.shape);labels[mask]=region['label'];origin[mask]=2
    return labels,origin

def region_features(rgba,labels):
    from scipy.ndimage import maximum_filter
    rgb=np.asarray(rgba)[...,:3];lum=rgb.mean(axis=2)/255;gx=np.max(np.abs(np.diff(rgb.astype(float)/255,axis=1,prepend=rgb[:,:1]/255)),axis=2);gy=np.max(np.abs(np.diff(rgb.astype(float)/255,axis=0,prepend=rgb[:1]/255)),axis=2);edges=maximum_filter(np.maximum(gx,gy),3);records={}
    for value in np.unique(labels):
        pixels=rgb[labels==value];keys=np.floor(pixels/32).astype('u1');colors,counts=np.unique(keys,axis=0,return_counts=True);rank=np.argsort(counts)[::-1][:8];mask=labels==value
        records[CLASS_NAMES[int(value)]]={'pixels':len(pixels),'channel_histograms':[np.histogram(pixels[:,i],bins=16,range=(0,256))[0].tolist() for i in range(3)],'dominant_colors':[{'rgb':np.rint(pixels[np.all(keys==colors[k],axis=1)].mean(axis=0)).astype(int).tolist(),'fraction':round(float(counts[k]/len(pixels)),5)} for k in rank],'dark_fraction':round(float((lum[mask]<.15).mean()),5),'bright_fraction':round(float((lum[mask]>.85).mean()),5),'edge_fraction':round(float((edges[mask]>.08).mean()),5),'scope':'Observed distribution/edges; not OCR, material recognition or physical lighting removal.'}
    return records

def save_masks(directory,image,labels,origin,native=None):
    from pathlib import Path
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True);rgba=np.asarray(image.convert('RGBA'));Image.fromarray(labels).save(directory/'labels.png');Image.fromarray(origin).save(directory/'origin.png')
    if native is not None:Image.fromarray(native.astype('u1')).save(directory/'native_labels.png')
    color=PALETTE[labels];overlay=rgba.copy();visible=labels>0;overlay[visible,:3]=np.rint(rgba[visible,:3]*.5+color[visible]*.5).astype('u1');Image.fromarray(overlay).save(directory/'overlay.png');Image.fromarray(color).save(directory/'segmentation.png')
    for value in np.unique(labels):Image.fromarray((labels==value).astype('u1')*255).save(directory/f'mask_{CLASS_NAMES[int(value)]}.png')
