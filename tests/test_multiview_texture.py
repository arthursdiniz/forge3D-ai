import numpy as np,trimesh
from PIL import Image
from backend.reference_atlas import bake_reference_views

def test_named_front_back_projection_colors_only_observed_surfaces_and_preserves_geometry(tmp_path):
    vertices=np.array([[-.5,-.5,.5],[.5,-.5,.5],[.5,.5,.5],[-.5,.5,.5],[-.5,-.5,-.5],[.5,-.5,-.5],[.5,.5,-.5],[-.5,.5,-.5]])
    faces=np.array([[0,1,2],[0,2,3],[4,6,5],[4,7,6]])
    uv=np.array([[0,0],[.45,0],[.45,1],[0,1],[.55,0],[1,0],[1,1],[.55,1]])
    mesh=trimesh.Trimesh(vertices=vertices,faces=faces,vertex_normals=np.array([[0,0,1]]*4+[[0,0,-1]]*4),visual=trimesh.visual.TextureVisuals(uv=uv),process=False)
    front=np.zeros((32,32,4),np.uint8);front[1:-1,1:-1]=[255,0,0,255]
    back=front.copy();back[1:-1,1:-1]=[0,0,255,255]
    report=bake_reference_views(trimesh.Scene(mesh),{'front':front,'back':back},64,tmp_path/'result.glb')
    pixels=np.asarray(Image.open(tmp_path/'textures/ReferenceAlbedo.png'))
    assert pixels[32,12,0]>240 and pixels[32,55,2]>240
    result=next(iter(trimesh.load(tmp_path/'result.glb',force='scene',process=False).geometry.values()))
    assert np.array_equal(result.faces,faces) and np.allclose(result.vertices,vertices)
    assert report['conditioned_geometry'] is False and report['views']==['front','back']
