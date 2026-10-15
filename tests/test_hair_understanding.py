import numpy as np
import trimesh
from PIL import Image,ImageDraw

def mask_image(style='spiky'):
    image=Image.new('L',(128,128),0);draw=ImageDraw.Draw(image)
    if style=='buzz':draw.ellipse((35,23,93,53),fill=255);draw.rectangle((0,36,128,128),fill=0)
    else:draw.polygon([(24,58),(20,35),(35,39),(36,13),(49,31),(62,4),(70,29),(87,8),(86,34),(109,22),(99,58),(84,72),(72,55),(52,74),(44,55)],fill=255)
    return np.asarray(image)>0

def test_observed_contour_guides_and_attributes_preserve_asymmetry():
    from backend.hair.understanding import analyze_hair
    report=analyze_hair(mask_image(),[.30,.32,.72,.78])
    assert len(report['tips'])>=3 and all('direction' in tip and 'width' in tip for tip in report['tips'])
    assert report['attributes']['volume']>0 and report['attributes']['spikes']>0
    assert not report['symmetry_forced'] and report['hidden_geometry_confidence']=='low'
    buzz=analyze_hair(mask_image('buzz'),[.30,.32,.72,.78],preset='buzz')
    assert buzz['attributes']['spikes']==0 and buzz['attributes']['volume']<=.04

def test_scalp_is_estimated_from_head_region_not_full_character_bounds():
    from backend.texture_engine.region_camera import RegionCamera
    from backend.hair.scalp import estimate_scalp
    scene=trimesh.Scene();scene.add_geometry(trimesh.creation.icosphere(subdivisions=2,radius=.15).apply_translation([0,.7,0]),geom_name='Head')
    scene.add_geometry(trimesh.creation.box([.6,1.0,.3]).apply_translation([0,-.1,0]),geom_name='Body')
    camera=RegionCamera(scene,'negative_y',128);xy=camera.coordinates(np.array([[-.13,.82,.1],[.13,.59,.1]]));box=[xy[0,0],xy[0,1],xy[1,0],xy[1,1]]
    report=estimate_scalp(scene,camera,box)
    assert report['status']=='reviewable' and .60<report['center'][1]<.85
    assert max(report['radii'])<.25 and report['method']!='character bounding box'

def test_mask_metrics_are_measured_and_missing_ground_truth_is_explicit():
    from backend.hair.metrics import silhouette_metrics
    target=np.zeros((64,64),bool);target[10:40,20:45]=True;candidate=target.copy()
    result=silhouette_metrics(candidate,target)
    assert result['iou']==1 and result['mean_contour_distance_pixels']==0
    assert silhouette_metrics(candidate,None)['status']=='not_measurable'

def test_head_mask_rejects_disconnected_collar_and_depth_only_bounds_ordering():
    from backend.hair.understanding import head_component,depth_ordering
    mask=mask_image();mask[110:120,40:70]=True
    cleaned=head_component(mask,[.1,0,.95,.85])
    assert not cleaned[110:120].any() and cleaned[20:60].any()
    depth=np.ones(mask.shape);depth[mask]=2
    ordering=depth_ordering(depth,cleaned,[.30,.32,.72,.78])
    assert ordering['status']=='bounded_relative' and abs(ordering['front_offset_fraction'])<=.04
    assert depth_ordering(np.ones(mask.shape),cleaned,[.30,.32,.72,.78])['front_offset_fraction']==0

def test_local_refinement_rejects_face_intrusion_and_silhouette_regression():
    from backend.hair.metrics import choose_refinement
    before={'iou':.6,'mean_contour_distance_pixels':8.}
    candidates=[{'occlusion':0,'metrics':{'iou':.64,'mean_contour_distance_pixels':6.}}, {'occlusion':50,'metrics':{'iou':.9,'mean_contour_distance_pixels':2.}}, {'occlusion':0,'metrics':{'iou':.5,'mean_contour_distance_pixels':4.}}]
    assert choose_refinement(candidates,before,8)==0
    assert choose_refinement(candidates[1:],before,8) is None

def test_manual_head_crop_does_not_reintroduce_short_hair_collar_pixels():
    from backend.hair.analysis import target_hair_box
    mask=np.zeros((100,100),bool);mask[5:24,40:60]=True
    box=target_hair_box(mask,[.4,.15,.6,.35],[.4,.2,.6,.4])
    assert box[3]==.4
    mask[40:55,40:60]=True
    assert target_hair_box(mask,[.4,.15,.6,.35],[.4,.2,.6,.4])[3]>.4

def test_refinement_keeps_original_when_better_iou_adds_a_bad_spike():
    from backend.hair.metrics import silhouette_metrics,choose_refinement
    target=np.zeros((128,128),bool);target[30:70,30:70]=True
    original=target.copy();original[30:34,30:70]=False
    spike=target.copy();spike[30,70:110]=True
    before=silhouette_metrics(original,target);after=silhouette_metrics(spike,target)
    assert after['iou']>before['iou'] and after['mean_contour_distance_pixels']>before['mean_contour_distance_pixels']
    assert choose_refinement([{'occlusion':0,'metrics':after}],before,8) is None
