import numpy as np
import pytest
import trimesh
from PIL import Image
from backend.texture_engine.identity import compare_geometry

def plane(z=.5,name='Face',color=(160,160,160,255),y=0):
    return trimesh.Trimesh(vertices=[[-.5,y-.5,z],[.5,y-.5,z],[.5,y+.5,z],[-.5,y+.5,z]],faces=[[0,1,2],[0,2,3]],vertex_normals=[[0,0,1]]*4,visual=trimesh.visual.TextureVisuals(uv=[[0,0],[1,0],[1,1],[0,1]],material=trimesh.visual.material.PBRMaterial(name=name,baseColorTexture=Image.new('RGBA',(64,64),color),normalTexture=Image.new('RGB',(8,8),(128,128,255)),metallicFactor=0,roughnessFactor=.65)),process=False)

def test_region_masks_alignment_and_protected_polygons():
    from backend.texture_engine.region_masks import editable_mask,source_coordinates
    points=np.array([[.3,.3],[.5,.5],[.7,.7],[.1,.1]])
    options={'source_box':[.1,.2,.9,.8],'target_box':[.2,.2,.8,.8],'protected':[[[.4,.4],[.6,.4],[.6,.6],[.4,.6]]]}
    assert editable_mask(points,options).tolist()==[True,False,True,False]
    assert np.allclose(source_coordinates(np.array([[.2,.2],[.8,.8]]),options),[[.1,.2],[.9,.8]])
    options.update(source_points=[[.1,.2],[.9,.2],[.1,.8]],target_points=[[.2,.2],[.8,.2],[.2,.8]])
    assert np.allclose(source_coordinates(np.array([[.5,.5]]),options),[[.5,.5]])

def test_regional_projection_preserves_every_external_pixel_and_data_map(tmp_path):
    from backend.texture_engine.face_refinement import refine_scene
    scene=trimesh.Scene();scene.add_geometry(plane(),node_name='face');scene.add_geometry(plane(-.5,'Back',(20,30,40,180)),node_name='back')
    options={'source_box':[0,0,1,1],'target_box':[.25,.25,.75,.75],'region':'face','front_axis':'negative_y','intensity':1,'feather_pixels':2,'minimum_cosine':.75,'reviewed_alignment':True,'protected':[[[.45,.45],[.55,.45],[.55,.55],[.45,.55]]]}
    image=np.full((128,128,4),[230,80,20,255],np.uint8)
    report=refine_scene(scene,image,options,tmp_path)
    assert report['regional']['status']=='improved_candidate' and report['regional']['outside_unchanged']
    result=trimesh.load(tmp_path/'model.glb',force='scene',process=False)
    assert compare_geometry(scene,result)['equivalent']
    for record in report['materials']:
        original=next(mesh.visual.material for mesh in scene.geometry.values() if mesh.visual.material.name==record['name'])
        material=next(mesh.visual.material for mesh in result.geometry.values() if mesh.visual.material.name==record['name'])
        mask=np.asarray(Image.open(tmp_path/record['maps']['edit_mask']))>0
        assert np.array_equal(np.asarray(original.baseColorTexture)[~mask],np.asarray(material.baseColorTexture)[~mask])
        assert np.array_equal(np.asarray(original.normalTexture),np.asarray(material.normalTexture))
        assert np.array_equal(np.asarray(original.baseColorTexture)[...,3],np.asarray(material.baseColorTexture)[...,3])
        if record['name']=='Back':assert not mask.any()
    assert report['regional']['metrics']['after']['rgb_mae']<report['regional']['metrics']['before']['rgb_mae']

def test_camera_front_preview_orientation_and_occlusion():
    from backend.texture_engine.region_camera import RegionCamera
    scene=trimesh.Scene(plane());camera=RegionCamera(scene,'negative_y',128)
    pixels=camera.coordinates(np.array([[0,.3,.5],[0,-.3,.5]]))
    assert pixels[0,1]<pixels[1,1]
    weights=camera.visibility(np.array([[0,0,.5],[0,0,-.5]]),np.array([[0,0,1],[0,0,1]]))
    assert weights[0]>.9 and weights[1]==0

def test_low_detail_reference_and_invalid_alignment_are_explicit():
    from backend.texture_engine.face_reference import crop_reference
    from backend.texture_engine.region_masks import source_coordinates
    report=crop_reference(Image.new('RGBA',(32,32)),[.2,.2,.8,.8])
    assert report['warnings'] and report['source_crop'].size[0]<32
    with pytest.raises(ValueError):source_coordinates(np.zeros((1,2)),{'source_points':[[0,0],[0,0],[0,0]],'target_points':[[0,0],[0,0],[0,0]]})

def test_rectangular_atlas_raster_preserves_dimensions():
    from backend.neural_texture import rasterize_positions
    mesh=plane();raster=rasterize_positions(mesh.vertices,mesh.faces,mesh.visual.uv,(64,32))
    assert raster.shape==(32,64,4) and raster[...,3].min()>.5

def test_region_camera_uses_linear_gltf_color_factor_and_projection_preserves_it(tmp_path):
    from backend.texture_engine.region_camera import RegionCamera
    from backend.texture_engine.face_refinement import refine_scene
    mesh=plane(color=(255,255,255,255));mesh.visual.material.baseColorFactor=[64,64,64,255];scene=trimesh.Scene(mesh)
    camera=RegionCamera(scene,'negative_y',128)
    assert np.allclose(camera.image[64,64,:3],[137,137,137],atol=1)
    options={'source_box':[0,0,1,1],'target_box':[.2,.2,.8,.8],'reviewed_alignment':True,'intensity':1,'feather_pixels':0,'minimum_cosine':.75}
    report=refine_scene(scene,np.full((128,128,4),[128,128,128,255],np.uint8),options,tmp_path)
    assert report['regional']['status']=='improved_candidate'
    restored=trimesh.load(tmp_path/'model.glb',force='scene',process=False);material=next(iter(restored.geometry.values())).visual.material
    assert np.array_equal(material.baseColorFactor,[64,64,64,255])
    assert report['regional']['metrics']['after']['rgb_mae']<.01

def test_opaque_material_preview_ignores_texture_alpha_but_does_not_change_the_map():
    from backend.texture_engine.region_camera import RegionCamera
    mesh=plane(color=(180,90,30,80));mesh.visual.material.alphaMode='OPAQUE'
    camera=RegionCamera(trimesh.Scene(mesh),'negative_y',64)
    assert camera.image[32,32,3]==255
    assert np.asarray(mesh.visual.material.baseColorTexture)[0,0,3]==80

def test_candidate_acceptance_requires_color_and_structure_evidence():
    from backend.texture_engine.texture_metrics import candidate_improved
    before={'status':'measured','rgb_mae':.2,'ssim':.8}
    assert not candidate_improved(before,{'status':'measured','rgb_mae':.1,'ssim':.3},100,True,128)
    assert candidate_improved(before,{'status':'measured','rgb_mae':.1,'ssim':.85},100,True,128)
    assert not candidate_improved(before,{'status':'measured','rgb_mae':.1,'ssim':.85},100,False,128)

def test_nearby_occluded_surface_cannot_receive_reference_pixels():
    from backend.texture_engine.region_camera import RegionCamera
    from backend.texture_engine.face_projection import project_region
    scene=trimesh.Scene();scene.add_geometry(plane(.5,'Visible'));scene.add_geometry(plane(.499,'Hidden'))
    camera=RegionCamera(scene,'negative_y',128)
    points=np.array([[0,0,.5],[0,0,.499]])
    normals=np.array([[0,0,1],[0,0,1]])
    _,confidence,_,_=project_region(camera,points,normals,np.full((128,128,4),[230,80,20,255],np.uint8),{'source_box':[0,0,1,1],'target_box':[0,0,1,1]})
    assert confidence[0]>.9 and confidence[1]==0

def test_visible_surface_uses_matching_triangle_in_the_pixel_footprint():
    from backend.texture_engine.region_camera import RegionCamera
    scene=trimesh.Scene(plane());camera=RegionCamera(scene,'negative_y',128)
    assert camera.visibility(np.array([[0,0,.5]]),np.array([[0,0,1]]),1,np.array([1]))[0]>.9

def test_inconclusive_version_retains_published_provenance(tmp_path):
    from backend.texture_engine.face_refinement import refine_scene
    options={'source_box':[0,0,1,1],'target_box':[.2,.2,.8,.8],'reviewed_alignment':True,'feather_pixels':0}
    folder=tmp_path/'first';scene=trimesh.Scene(plane())
    report=refine_scene(scene,np.full((16,16,4),[230,80,20,255],np.uint8),options,folder)
    assert report['regional']['status']=='inconclusive_previous_retained'
    assert report['copied_percent']==0
    provenance=np.asarray(Image.open(folder/report['materials'][0]['maps']['provenance']))
    assert not np.any(np.isin(provenance,[1,5]))
    following=tmp_path/'following'
    again=refine_scene(trimesh.load(folder/'model.glb',force='scene',process=False),np.full((16,16,4),[230,80,20,255],np.uint8),options,following,folder)
    assert again['copied_percent']==0
