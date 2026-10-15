"""Reproject existing real neural views only after controls match this geometry."""
import json
from pathlib import Path
import numpy as np

class CachedViews:
    def __init__(self,scene,axis,source_folder):
        self.valid=False;self.reason='No existing neural view cache.';self.views={};self.controls=None
        if not source_folder:return
        try:
            from PIL import Image
            from .native import NativeControls
            folder=Path(source_folder);report=json.loads((folder/'neural.json').read_text());size=int(report['native_resolution'])
            if report.get('offline') is not True or report.get('joint_views')!=6 or size not in [128,512,768]:raise ValueError('Unsupported cached profile.')
            self.controls=NativeControls(scene,axis,size)
            for index,view in enumerate(self.controls.views):
                for offset,label in [(0,'position'),(3,'normal')]:
                    expected=np.rint(self.controls.controls[index,offset:offset+3].transpose(1,2,0)*255).astype('u1')
                    actual=np.asarray(Image.open(folder/'neural_views'/(view+'_'+label+'.png')).convert('RGB'))
                    if not np.array_equal(actual,expected):raise ValueError('Cached controls do not match current geometry/cameras; preserving previous texture.')
                image=Image.open(folder/'neural_views'/(view+'.png')).convert('RGB')
                if image.size!=(size,size):raise ValueError('Cached neural view size mismatch.')
                self.views[view]=np.dstack([np.asarray(image),np.uint8(self.controls.rasters[view][...,3]>.5)*255])
            self.valid=True;self.reason='Geometry/camera position and normal controls match all six cached views; no new inference.'
        except (OSError,ValueError,KeyError,RuntimeError) as error:self.reason=str(error)[-600:]

    def project(self,points,normals):
        from .texture_fusion import fuse_observations,gradient_reference
        if not self.valid:raise ValueError(self.reason)
        colors=[];weights=[];gradients=[]
        for view,rgba in self.views.items():
            rgb,weight=self.controls.project(view,points,normals,rgba);edge,_=self.controls.project(view,points,normals,gradient_reference(rgba))
            colors.append(rgb);weights.append(weight);gradients.append(edge[:,0])
        result=fuse_observations(np.stack(colors,axis=1),np.stack(weights,axis=1),np.stack(gradients,axis=1),'robust')
        return result['rgb'],result['confidence']
