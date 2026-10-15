import numpy as np
import trimesh
from backend.reference_texture import project_reference_colors
from backend.texture_engine.native import NativeControls

def test_reference_angle_confidence_does_not_desaturate_observed_rgb():
    vertices=np.array([[-.5,-.5,.5],[.5,-.5,.5],[.5,.5,.5],[-.5,.5,.5]])
    rgba=np.full((64,64,4),[230,45,20,220],np.uint8)
    colors,weights=project_reference_colors(vertices,[[0,1,2],[0,2,3]],[[0,0,.5]],[[.866,0,.5]],rgba)
    assert 0<weights[0]<.8
    assert np.allclose(colors[0],np.array([230,45,20])/255,atol=1e-6)

def test_native_angle_confidence_does_not_desaturate_observed_rgb():
    mesh=trimesh.creation.box();controls=NativeControls(trimesh.Scene(mesh),'negative_y',64)
    colors,weights=controls.project('front',np.array([[0,0,.5]]),np.array([[.866,0,.5]]),np.full((64,64,4),[230,45,20,255],np.uint8))
    assert 0<weights[0]<.8
    assert np.allclose(colors[0],np.array([230,45,20])/255,atol=1e-6)

def test_robust_fusion_blends_smooth_agreement_and_protects_conflicts_and_edges():
    from backend.texture_engine.texture_fusion import fuse_observations
    colors=np.array([[[.8,.1,.05],[.82,.11,.06]],[[.8,.1,.05],[.1,.8,.05]],[[.8,.1,.05],[.82,.11,.06]]],np.float32)
    weights=np.tile([.8,.7],(3,1));gradients=np.array([[0,0],[0,0],[.2,0]])
    result=fuse_observations(colors,weights,gradients,'robust')
    assert result['mixed'].tolist()==[True,False,False]
    assert .8<result['rgb'][0,0]<.82
    assert np.array_equal(result['rgb'][1:],colors[1:,0])
    assert result['conflict'][1] and result['contributors'][0]==3
    winner=fuse_observations(colors,weights,gradients,'winner')
    assert np.array_equal(winner['rgb'],colors[:,0]) and not winner['mixed'].any()

def test_fusion_unknown_stays_neutral_and_never_gains_false_confidence():
    from backend.texture_engine.texture_fusion import fuse_observations
    from backend.reference_texture import NEUTRAL
    result=fuse_observations(np.ones((2,2,3)),np.array([[0,0],[.2,0]]),np.zeros((2,2)),'robust')
    assert np.allclose(result['rgb'][0],NEUTRAL) and result['source_view'][0]==0
    assert result['confidence'].tolist()==[0,.2]
