import numpy as np
import trimesh
from PIL import Image

def test_reference_atlas_preserves_geometry_and_keeps_unobserved_back_neutral(tmp_path):
    from backend.reference_atlas import bake_reference_atlas
    vertices=np.array([[-.5,-.5,.5],[.5,-.5,.5],[.5,.5,.5],[-.5,.5,.5],[-.5,-.5,-.5],[.5,-.5,-.5],[.5,.5,-.5],[-.5,.5,-.5]])
    faces=np.array([[0,1,2],[0,2,3],[4,6,5],[4,7,6]])
    uv=np.array([[0,0],[.45,0],[.45,1],[0,1],[.55,0],[1,0],[1,1],[.55,1]])
    mesh=trimesh.Trimesh(vertices=vertices,faces=faces,vertex_normals=np.array([[0,0,1]]*4+[[0,0,-1]]*4),visual=trimesh.visual.TextureVisuals(uv=uv),process=False)
    scene=trimesh.Scene(mesh)
    rgba=np.zeros((32,32,4),np.uint8);rgba[:16]=[255,0,0,255];rgba[16:]=[0,0,255,255]
    report=bake_reference_atlas(scene,rgba,64,tmp_path/'textured.glb')
    result=trimesh.load(tmp_path/'textured.glb',force='scene',process=False)
    restored=next(iter(result.geometry.values()))
    assert np.array_equal(restored.faces,faces) and np.allclose(restored.vertices,vertices)
    assert np.array_equal(mesh.vertices,vertices) and np.array_equal(mesh.faces,faces)
    pixels=np.asarray(Image.open(tmp_path/'textures/ReferenceAlbedo.png'))
    assert pixels[8,8,0]>240 and pixels[56,8,2]>240
    assert np.allclose(pixels[32,56],[188,188,188],atol=1)
    assert report['method']=='reference_visible_front' and report['hidden_surface']=='neutral'
    assert 40<report['visible_surface_texel_percent']<60

def test_projection_preserves_an_existing_baked_normal_map(tmp_path):
    from backend.reference_atlas import bake_reference_views
    mesh=trimesh.creation.box()
    mesh.visual=trimesh.visual.TextureVisuals(uv=np.zeros((len(mesh.vertices),2)),material=trimesh.visual.material.PBRMaterial(normalTexture=Image.new('RGB',(8,8),(128,128,255))))
    # Use a real non-overlapping planar UV fixture for the atlas.
    vertices=np.array([[-.5,-.5,.5],[.5,-.5,.5],[.5,.5,.5],[-.5,.5,.5]])
    mesh=trimesh.Trimesh(vertices=vertices,faces=[[0,1,2],[0,2,3]],visual=trimesh.visual.TextureVisuals(uv=[[0,0],[1,0],[1,1],[0,1]],material=mesh.visual.material),process=False)
    rgba=np.zeros((32,32,4),np.uint8);rgba[1:-1,1:-1]=[255,0,0,255]
    report=bake_reference_views(trimesh.Scene(mesh),{'front':rgba},64,tmp_path/'projected.glb')
    restored=next(iter(trimesh.load(tmp_path/'projected.glb',force='scene',process=False).geometry.values()))
    assert restored.visual.material.normalTexture is not None
    assert np.array_equal(np.asarray(restored.visual.material.normalTexture),np.asarray(mesh.visual.material.normalTexture))
    assert report['normal_map_preserved'] is True
