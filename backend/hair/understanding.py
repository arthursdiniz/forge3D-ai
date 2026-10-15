"""Hair silhouettes and semantic regions become reviewable measured guides."""
import numpy as np

from .presets import PRESETS

def head_component(mask,box):
    """Keep the largest observed head component, excluding crop padding/clothing noise."""
    import cv2
    mask=np.asarray(mask,bool).copy();h,w=mask.shape;yy,xx=np.indices(mask.shape);l,t,r,b=box
    mask&=(xx/w>=l)&(xx/w<r)&(yy/h>=t)&(yy/h<b)
    count,labels,stats,_=cv2.connectedComponentsWithStats(mask.astype('u1'),8)
    if count<=1:return mask
    return labels==(1+np.argmax(stats[1:,cv2.CC_STAT_AREA]))

def depth_ordering(depth,mask,face_box):
    """A bounded layer cue; inverse depth never becomes metric displacement."""
    result={'status':'unavailable_or_ambiguous','front_offset_fraction':0.,'metric_depth':False}
    if depth is None:return result
    depth=np.asarray(depth);h,w=depth.shape;yy,xx=np.indices(depth.shape);l,t,r,b=face_box
    valid=np.isfinite(depth)&(depth>0);hair=depth[valid&mask];face=depth[valid&~mask&(xx/w>=l)&(xx/w<r)&(yy/h>=t)&(yy/h<b)]
    if len(hair)<32 or len(face)<32:return result
    low,high=np.percentile(depth[valid],[10,90]);spread=high-low
    if spread<1e-5:return result
    contrast=float(np.clip((np.median(hair)-np.median(face))/spread,-1,1))
    return {**result,'status':'bounded_relative','hair_face_inverse_depth_contrast':contrast,'front_offset_fraction':contrast*.04,'scope':'At most 4% of local cranial depth radius, constrained outside the existing front surface; not physical thickness.'}

def analyze_hair(mask,face_box,rgb=None,depth=None,preset='auto'):
    import cv2
    from scipy.ndimage import gaussian_filter1d,distance_transform_edt
    from scipy.signal import find_peaks
    if preset not in PRESETS:raise ValueError('Unknown hair preset.')
    mask=np.asarray(mask,bool);h,w=mask.shape;ys,xs=np.where(mask)
    if len(xs)<32:return {'status':'manual_required','tips':[],'attributes':{},'reason':'Insufficient observed hair mask; original retained.'}
    l,t,r,b=face_box;fw=r-l;fh=b-t;cx=(l+r)/2;cy=t+fh*.12
    contours,_=cv2.findContours(mask.astype('u1'),cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_NONE);contour=max(contours,key=cv2.contourArea)[:,0,:].astype(float);xy=contour/np.array([w,h])
    radial=np.linalg.norm((xy-[cx,cy])/np.array([max(fw/2,1e-6),max(fh*.55,1e-6)]),axis=1)
    smooth=gaussian_filter1d(radial,1.1,mode='wrap');length=len(smooth)
    extended=np.tile(smooth,3);peaks,_=find_peaks(extended,prominence=.07,distance=max(3,length//35));peaks=peaks[(peaks>=length)&(peaks<2*length)]-length
    distance=distance_transform_edt(mask);tips=[]
    for index in sorted(peaks,key=lambda i:smooth[i],reverse=True)[:32]:
        tip=xy[index];direction=tip-[cx,cy];magnitude=np.linalg.norm(direction)
        if magnitude<1e-8:continue
        zone='fringe' if tip[1]>t+fh*.12 and l<tip[0]<r else ('top' if tip[1]<t else ('left' if tip[0]<cx else 'right'))
        root=np.array([cx,cy])+direction*.5;px,py=np.rint(root*[w,h]).astype(int);px=np.clip(px,0,w-1);py=np.clip(py,0,h-1)
        step=max(3,min(12,length//50));a=contour[(index-step)%length]-contour[index];bb=contour[(index+step)%length]-contour[index];angle=float(np.degrees(np.arccos(np.clip(np.dot(a,bb)/max(np.linalg.norm(a)*np.linalg.norm(bb),1e-9),-1,1))))
        tips.append({'tip':tip.tolist(),'root_2d':root.tolist(),'direction':(direction/magnitude).tolist(),'width':float(np.clip(distance[py,px]/max(w*fw,1e-6),.035,.23)),'zone':zone,'pointed':angle<140,'contour_angle_degrees':angle,'source':'observed contour; root/direction are geometric estimates'})
    above=(t-ys.min()/h)/max(fh,1e-6);side=(xs.max()-xs.min())/max(w*fw,1e-6);below=(ys.max()/h-b)/max(fh,1e-6)
    spike_count=sum(tip['zone']!='fringe' and tip['pointed'] for tip in tips)
    selected=preset if preset!='auto' else ('anime_spiky' if spike_count>=3 and above>.3 else ('long' if below>.4 else ('anime_fluffy' if side>1.5 else 'short_volume')))
    volume=float(np.clip(above*.15+(side-1)*.08,.015,.3));spikes=float(np.clip(spike_count/10,0,1))
    if selected=='buzz':volume=.025;spikes=0;tips=[]
    elif selected=='close_short':volume=min(volume,.06);spikes=0;tips=[]
    elif selected in ['anime_fluffy','afro','curly','wavy']:spikes=0
    attributes={'volume':volume,'lateral_volume':float(np.clip((side-1)*.15,.01,.3)),'back_volume':volume*.6,'top_height':float(np.clip(above*.2,.01,.4)),'spikes':spikes,'thickness':.05,'fringe':float(sum(tip['zone']=='fringe' for tip in tips)/max(len(tips),1)),'length':float(np.clip(max(above,below)*.4,.02,1.5)),'curvature':.15 if selected in ['curly','wavy','anime_fluffy','afro'] else .03,'asymmetry':float(abs((xs/w<cx).sum()-(xs/w>=cx).sum())/len(xs))}
    colors=None
    if rgb is not None:colors=np.median(np.asarray(rgb)[mask,:3],axis=0).round().astype(int).tolist()
    layers={'ordering':'Observed hair in front of visible face where semantic masks overlap; rear geometry unknown','relative_depth_used':False}
    if depth is not None:
        values=np.asarray(depth)[mask];values=values[np.isfinite(values)&(values>0)]
        if len(values)>=32:layers.update(relative_depth_used=True,hair_depth_percentiles=np.percentile(values,[10,50,90]).tolist(),scope='Relative ordering only; no metric thickness or direct extrusion.')
    return {'status':'reviewable','preset':selected,'preset_source':'user' if preset!='auto' else 'silhouette heuristic, not learned universal hairstyle classification','attributes':attributes,'tips':tips,'bounds':[float(xs.min()/w),float(ys.min()/h),float((xs.max()+1)/w),float((ys.max()+1)/h)],'mask_pixels':len(xs),'hair_color':colors,'layers':layers,'symmetry_forced':False,'hidden_geometry_confidence':'low','visible_views':['front'],'warnings':['Single frontal reference cannot establish backside identity.']}
