import numpy as np


def test_ratio_comparison_is_projected_measurement_not_anatomy_score():
    from backend.character_quality import compare_proportions
    original={'proportions':{'left_upper_arm_to_torso':{'value':.5,'scope':'projected_2d_ratio'}},'view':'front'}
    candidate={'proportions':{'left_upper_arm_to_torso':{'value':.6,'scope':'projected_2d_ratio'}},'view':'front'}
    report=compare_proportions(original,candidate)
    assert report['measurements']['left_upper_arm_to_torso']['relative_difference']==.2
    assert report['anatomy_score'] is None
    original['view']='unknown'
    assert compare_proportions(original,candidate)['status']=='NOT_MEASURABLE'


def test_opaque_reference_does_not_create_fake_silhouette_measurement():
    from backend.character_quality import silhouette_measurement
    rgba=np.full((32,32,4),255,np.uint8)
    report=silhouette_measurement([[0,0,0],[1,0,0],[0,1,0]],[[0,1,2]],rgba)
    assert report['status']=='NOT_MEASURABLE' and report.get('iou') is None


def test_view_transform_uses_native_hunyuan_view_convention():
    from backend.character_quality import view_vertices
    vertices=np.array([[1,2,3.]])
    assert np.array_equal(view_vertices(vertices,'left'),[[-3,2,1]])
    assert np.array_equal(view_vertices(vertices,'back'),[[-1,2,-3]])
