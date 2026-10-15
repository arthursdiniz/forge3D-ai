import numpy as np
from PIL import Image


def test_portrait_mapping_never_invents_fine_clothing_or_unknown_classes():
    from backend.texture_engine.semantic_masks import map_native
    labels=np.array([[0,1,2,3,4,5,6,200]],dtype='u1')
    result=map_native(labels,[0,0,1,1],np.full((1,8),255,'u1'))
    assert result.tolist()==[[1,4,5,6,3,2,7,0]]
    assert 16 not in result and 17 not in result


def test_crop_outside_is_unknown_and_only_actual_transparency_is_background():
    from backend.texture_engine.semantic_masks import map_native
    alpha=np.full((8,8),255,'u1');alpha[0]=0
    labels=map_native(np.ones((8,8),'u1'),[.25,.25,.75,.75],alpha)
    assert np.all(labels[2:6,2:6]==4) and labels[7,7]==0 and np.all(labels[0]==1)


def test_manual_strokes_preserve_learned_labels_and_restore_intrinsic_pixels():
    from backend.texture_engine.semantic_masks import apply_strokes
    learned=np.full((100,200),4,'u1')
    strokes=[{'points':[[.5,.5]],'radius':.04,'label':16,'operation':'paint'}]
    labels,origin=apply_strokes(learned,strokes)
    assert labels[50,100]==16 and origin[50,100]==2
    assert labels[10,10]==4 and np.all(learned==4)
    labels,_=apply_strokes(learned,strokes+[{'points':[[.5,.5]],'radius':.05,'label':0,'operation':'restore'}])
    assert np.all(labels==learned)


def test_region_features_keep_pattern_variation_instead_of_only_average_rgb():
    from backend.texture_engine.semantic_masks import region_features
    rgba=np.full((32,32,4),255,'u1');rgba[:16,:,:3]=0;labels=np.full((32,32),7,'u1')
    report=region_features(rgba,labels)['clothes']
    assert len(report['dominant_colors'])>=2 and report['pixels']==1024
    assert report['dark_fraction']==.5 and report['bright_fraction']==.5
    assert report['edge_fraction']>0 and sum(report['channel_histograms'][0])==1024


def test_missing_weights_returns_explicit_manual_profile_without_fake_inference(tmp_path):
    from backend.texture_engine.semantic_inference import segment_image
    image=Image.new('RGBA',(64,64),(200,100,30,255))
    labels,origin,report=segment_image(image,tmp_path,[0,0,1,1],'anime',tmp_path/'result')
    assert report['status']=='manual_required' and not report['neural_executed']
    assert np.all(labels==0) and np.all(origin==0)


def test_manual_uniform_polygon_labels_pixels_without_inventing_a_neural_class():
    from backend.texture_engine.semantic_masks import apply_polygons
    learned=np.zeros((100,100),'u1');labels,origin=apply_polygons(learned,np.zeros_like(learned),[{'points':[[.3,.3],[.7,.3],[.7,.7],[.3,.7]],'label':16}])
    assert labels[50,50]==16 and origin[50,50]==2 and labels[10,10]==0 and not learned.any()
