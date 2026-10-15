"""Head views share one anatomical review frame and actual normal-based clay lighting."""
import numpy as np
from backend.texture_engine.region_camera import RegionCamera

def head_view(scene,axis,frame,box,scalp,size=768,yaw=0,clay=False):
    l,t,r,b=box;center=np.array(frame['center'],float);scale=frame['scale'];center[0]+=((l+r)/2-.5)/scale;center[1]+=(.5-(t+b)/2)/scale;center[2]=scalp['center'][2]
    angle=np.deg2rad(yaw);center=center@np.array([[np.cos(angle),0,np.sin(angle)],[0,1,0],[-np.sin(angle),0,np.cos(angle)]])
    head_frame={**frame,'center':center.tolist(),'scale':scale/max(r-l,b-t)};camera=RegionCamera(scene,axis,size,head_frame,yaw)
    if not clay:return camera.image
    normals=camera.buffers[1][...,:3];light=np.array([-.4,.6,1.]);light/=np.linalg.norm(light);brightness=.25+.75*np.maximum(0,normals@light);visible=camera.buffers[0][...,3]>.5
    image=np.zeros((size,size,4),np.uint8);image[...,:3]=np.rint(brightness[...,None]*np.array([190.,190.,190.])).astype('u1');image[...,3]=visible.astype('u1')*255;return image
