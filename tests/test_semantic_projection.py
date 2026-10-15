import numpy as np
import trimesh
from tests.test_region_refinement import plane


def test_semantic_projection_blocks_hair_on_face_and_hidden_surface():
    from backend.texture_engine.semantic_projection import project_semantic
    from backend.texture_engine.region_camera import RegionCamera
    scene=trimesh.Scene(plane());camera=RegionCamera(scene,'negative_y',128)
    source=np.full((64,64),4,'u1');target=np.full((128,128),3,'u1');rgba=np.full((64,64,4),[25,30,40,255],'u1')
    registration={'source_box':[0,0,1,1],'target_box':[.05,.05,.95,.95],'minimum_cosine':.5}
    result=project_semantic(camera,np.array([[0,0,.5],[0,0,-.5]]),np.array([[0,0,1],[0,0,1]]),rgba,source,target,registration,1,np.array([1,1]))
    assert result['weight'].tolist()==[0,0] and result['conflict'][0]
    target[:]=4
    result=project_semantic(camera,np.array([[0,0,.5],[0,0,-.5]]),np.array([[0,0,1],[0,0,1]]),rgba,source,target,registration,1,np.array([1,1]))
    assert result['weight'][0]>.9 and result['weight'][1]==0
    assert np.allclose(result['rgb'][0],[25/255,30/255,40/255])


def test_unknown_target_requires_explicit_reviewed_policy():
    from backend.texture_engine.semantic_projection import semantic_allowed
    source=np.array([4,5,7,0,1]);target=np.array([0,4,7,3,4])
    assert semantic_allowed(source,target,False).tolist()==[False,False,True,False,False]
    assert semantic_allowed(source,target,True).tolist()==[True,False,True,False,False]


def test_multiview_fusion_does_not_average_incompatible_semantic_regions():
    from backend.texture_engine.semantic_fusion import fuse_semantic
    colors=np.array([[[.1,.1,.1],[1,.8,.7]]]);weights=np.array([[.9,.8]]);classes=np.array([[4,3]],'u1')
    result=fuse_semantic(colors,weights,np.zeros((1,2)),classes)
    assert np.allclose(result['rgb'],[[.1,.1,.1]]) and result['class'].tolist()==[4]
    assert result['semantic_conflict'].tolist()==[True] and not result['mixed'][0]


def test_surface_fill_requires_same_component_class_and_bounded_distance():
    from backend.texture_engine.semantic_fusion import surface_fill
    positions=np.array([[0,0,0],[.001,0,0],[.002,0,0],[.5,0,0]])
    colors=np.array([[1,0,0],[0,0,0],[0,0,0],[0,0,0]],float);observed=np.array([True,False,False,False]);classes=np.array([4,4,3,4]);components=np.array([0,1,0,0]);normals=np.tile([0,0,1],(4,1))
    result,filled=surface_fill(positions,normals,colors,observed,classes,components,.01)
    assert not filled.any() and np.array_equal(result,colors)
    components[1]=0
    result,filled=surface_fill(positions,normals,colors,observed,classes,components,.01)
    assert filled.tolist()==[False,True,False,False] and result[1].tolist()==[1,0,0]


def test_protected_polygon_is_carried_to_completion_even_without_reference_color():
    from backend.texture_engine.semantic_projection import project_semantic
    from backend.texture_engine.region_camera import RegionCamera
    camera=RegionCamera(trimesh.Scene(plane()),'negative_y',128)
    options={'source_box':[0,0,1,1],'target_box':[0,0,1,1],'protected':[[[.4,.4],[.6,.4],[.6,.6],[.4,.6]]]}
    result=project_semantic(camera,np.array([[0,0,.5]]),np.array([[0,0,1]]),np.full((64,64,4),255,'u1'),np.full((64,64),4,'u1'),np.zeros((128,128),'u1'),options)
    assert result['protected'].tolist()==[True] and result['weight'][0]==0


def test_generated_categories_are_nearest_sampled_without_inventing_midpoint_class():
    from backend.texture_engine.semantic_paint import sample_generated_labels
    from backend.texture_engine.native import NativeControls
    controls=NativeControls(trimesh.Scene(plane()),'negative_y',32);labels=np.full((32,32),4,'u1');labels[:,16:]=6
    result=sample_generated_labels(controls,'front',np.array([[0,0,.5]]),labels)
    assert result.tolist()==[6]


def test_back_view_portrait_crop_comes_from_reviewed_head_surface_not_face_detection():
    from backend.texture_engine.semantic_paint import generated_head_crop
    from backend.texture_engine.native import NativeControls
    from backend.texture_engine.region_camera import RegionCamera
    scene=trimesh.Scene();scene.add_geometry(trimesh.creation.icosphere(subdivisions=2,radius=.3).apply_translation([0,2,0]));scene.add_geometry(trimesh.creation.box([.8,1.5,.4]).apply_translation([0,.4,0]));camera=RegionCamera(scene,'negative_y',128);controls=NativeControls(scene,'negative_y',32)
    crop=generated_head_crop(controls,'back',scene,{'front_axis':'negative_y','views':{'front':{'target':{'portrait_crop':[.3,0,.7,.35]},'camera_frame':camera.frame}}})
    assert crop is not None and 0<crop[0]<crop[2]<1 and 0<=crop[1]<crop[3]<.5 and crop[2]-crop[0]<.5


def test_rotated_render_metrics_use_canonical_surface_samples_once():
    from backend.texture_engine.semantic_paint import canonical_camera_samples
    from backend.texture_engine.region_camera import RegionCamera
    camera=RegionCamera(trimesh.Scene(trimesh.creation.icosphere(subdivisions=2)),'negative_y',64,yaw=180)
    points,normals=canonical_camera_samples(camera);occupied=camera.buffers[0][...,3].ravel()>.5;rows,cols=np.indices((64,64));expected=np.column_stack([(cols.ravel()+.5)/64,(rows.ravel()+.5)/64])
    # GPU barycentric interpolation differs by far less than .01 pixel at64px.
    assert np.allclose(camera.coordinates(points)[occupied],expected[occupied],atol=1e-4)
    assert np.isfinite(normals).all()


def test_target_face_identity_survives_transparent_or_absent_reference_pixels():
    from backend.texture_engine.semantic_atlas import atlas_observations
    from backend.texture_engine.semantic_paint import completion_allowed
    from backend.texture_engine.region_camera import RegionCamera
    camera=RegionCamera(trimesh.Scene(plane()),'negative_y',64)
    samples={'points':np.array([[0,0,.5]]),'normals':np.array([[0,0,1]]),'faces':np.array([1.])}
    view={'camera':camera,'rgba':np.zeros((64,64,4),'u1'),'source_labels':np.ones((64,64),'u1'),'target_labels':np.full((64,64),3,'u1'),'source_origin':np.zeros((64,64),'u1'),'registration':{'source_box':[0,0,1,1],'target_box':[0,0,1,1]}}
    data=atlas_observations(samples,[view],1)
    assert data['target_class'].tolist()==[3] and not data['weight'].any()
    assert not completion_allowed(np.array([False]),data['target_class'],np.array([4]),np.array([False])).any()
