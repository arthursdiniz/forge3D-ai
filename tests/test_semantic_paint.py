import json
import numpy as np
import trimesh
from PIL import Image
from tests.test_region_refinement import plane


def context(tmp_path,scene):
    from backend.texture_engine.region_camera import RegionCamera
    folder=tmp_path/'analysis';view=folder/'views/front';view.mkdir(parents=True)
    camera=RegionCamera(scene,'negative_y',128)
    Image.new('RGBA',(64,64),(20,40,90,255)).save(view/'source.png')
    Image.fromarray(np.full((64,64),4,'u1')).save(view/'source_labels.png');Image.fromarray(np.ones((64,64),'u1')).save(view/'source_origin.png')
    target=np.full((128,128),3,'u1');target[:,:64]=4;Image.fromarray(target).save(view/'target_labels.png')
    return {'directory':str(folder),'front_axis':'negative_y','camera_resolution':128,'views':{'front':{'camera_frame':camera.frame,'registration':{'source_box':[0,0,1,1],'target_box':[.05,.05,.95,.95],'minimum_cosine':.5}}}}


def test_reference_fidelity_paints_only_hair_and_preserves_geometry_channels(tmp_path):
    from backend.texture_engine.semantic_paint import paint_semantic
    from backend.texture_engine.identity import compare_geometry
    scene=trimesh.Scene(plane());analysis=context(tmp_path,scene)
    report=paint_semantic(scene,analysis,{'classes':['hair'],'protected_classes':['face'],'intensity':1,'seam_correction':False,'surface_fill':False,'reviewed_alignment':True},tmp_path/'result',tmp_path)
    result=trimesh.load(tmp_path/'result/model.glb',force='scene',process=False)
    assert compare_geometry(scene,result)['equivalent'] and report['semantic']['protected_pixels_equal']
    record=report['materials'][0];mask=np.asarray(Image.open(tmp_path/'result'/record['maps']['edit_mask']))>0
    before=next(iter(scene.geometry.values()));after=next(iter(result.geometry.values()));a=np.asarray(before.visual.material.baseColorTexture);b=np.asarray(after.visual.material.baseColorTexture)
    assert mask.any() and np.array_equal(a[~mask],b[~mask]) and np.array_equal(a[...,3],b[...,3])
    assert np.array_equal(before.visual.uv,after.visual.uv) and np.allclose(before.vertex_normals,after.vertex_normals,atol=1e-6)
    assert np.array_equal(np.asarray(before.visual.material.normalTexture),np.asarray(after.visual.material.normalTexture))
    assert report['semantic']['blocked_cross_class_texels']>0 and report['semantic']['painted_classes']==['hair']


def test_unreviewed_alignment_cannot_publish_semantic_texture(tmp_path):
    import pytest
    from backend.texture_engine.semantic_paint import paint_semantic
    scene=trimesh.Scene(plane());analysis=context(tmp_path,scene)
    with pytest.raises(ValueError):paint_semantic(scene,analysis,{'reviewed_alignment':False},tmp_path/'result',tmp_path)
    assert not (tmp_path/'result/model.glb').exists()


def test_semantic_neural_completion_never_overwrites_observed_or_protected_pixels():
    from backend.texture_engine.semantic_paint import completion_allowed
    observed=np.array([True,False,False,False]);target=np.array([4,4,0,3]);generated=np.array([4,4,5,3]);protected=np.array([False,False,False,True])
    assert completion_allowed(observed,target,generated,protected).tolist()==[False,True,False,False]


def test_blended_reference_texels_record_their_actual_mixture_weight(tmp_path):
    from backend.texture_engine.semantic_paint import paint_semantic
    scene=trimesh.Scene(plane());analysis=context(tmp_path,scene)
    report=paint_semantic(scene,analysis,{'classes':['hair'],'intensity':.5,'seam_correction':False,'reviewed_alignment':True},tmp_path/'result',tmp_path)
    maps=report['materials'][0]['maps'];origin=np.asarray(Image.open(tmp_path/'result'/maps['semantic_origin']));weight=np.asarray(Image.open(tmp_path/'result'/maps['blend_weight']))
    assert (origin==5).any() and np.all(weight[origin==5]==128)
