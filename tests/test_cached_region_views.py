import json
import numpy as np
import trimesh
from PIL import Image

def test_cached_views_require_matching_controls_and_return_unmodified_observed_colors(tmp_path):
    from backend.texture_engine.native import NativeControls
    from backend.texture_engine.cached_views import CachedViews
    scene=trimesh.Scene(trimesh.creation.box());controls=NativeControls(scene,'negative_y',128);folder=tmp_path/'neural_views';folder.mkdir()
    (tmp_path/'neural.json').write_text(json.dumps({'offline':True,'joint_views':6,'native_resolution':128}))
    for index,view in enumerate(controls.views):
        Image.new('RGB',(128,128),(230,45,20)).save(folder/(view+'.png'))
        for offset,label in [(0,'position'),(3,'normal')]:Image.fromarray(np.rint(controls.controls[index,offset:offset+3].transpose(1,2,0)*255).astype('u1')).save(folder/(view+'_'+label+'.png'))
    cache=CachedViews(scene,'negative_y',tmp_path);assert cache.valid
    colors,weights=cache.project(np.array([[0,0,.5]]),np.array([[.866,0,.5]]))
    assert weights[0]>0 and np.allclose(colors[0],np.array([230,45,20])/255,atol=1e-6)
    Image.new('RGB',(128,128)).save(folder/'front_position.png')
    assert not CachedViews(scene,'negative_y',tmp_path).valid
