import numpy as np
import trimesh

def fixture():
    mesh=trimesh.Trimesh(vertices=[[0,0,0],[1,0,0],[0,1,0],[0,0,0],[1,0,0],[0,-1,0]],faces=[[0,1,2],[3,5,4]],vertex_normals=[[0,0,1]]*6,visual=trimesh.visual.TextureVisuals(uv=[[.1,.1],[.4,.1],[.1,.4],[.6,.1],[.9,.1],[.6,.4]]),process=False)
    image=np.full((64,64,4),[150,150,150,255],np.uint8);image[:,32:,:3]=154
    return mesh,image

def test_local_seam_correction_never_touches_protected_or_high_contrast_pixels():
    from backend.texture_engine.texture_seams import inspect_seams,correct_seams
    mesh,image=fixture();mask=np.zeros((64,64),bool)
    diagnostics=inspect_seams(mesh,image);assert diagnostics['sample_pairs']>=2
    result=correct_seams(mesh,image,mask);assert np.array_equal(result,image)
    mask[:]=True;result=correct_seams(mesh,image,mask);assert not np.array_equal(result,image)
    image[:,32:,:3]=20;assert np.array_equal(correct_seams(mesh,image,mask),image)

def test_uv_density_is_a_measurement_and_cannot_trigger_unwrap():
    from backend.texture_engine.texture_seams import uv_density
    mesh,image=fixture();uv=mesh.visual.uv.copy();report=uv_density(mesh,np.ones(image.shape[:2],bool))
    assert report['median_texels_per_world_unit']>0 and report['uv_changed'] is False
    assert np.array_equal(mesh.visual.uv,uv)
