import pytest


def test_landmark_relations_use_real_confidence_and_preserve_stylized_design():
    from backend.character_understanding import summarize_character
    points={name:{'x':x,'y':y,'visibility':.95,'presence':.96,'source':'mediapipe'} for name,x,y in [('left_shoulder',.4,.3),('right_shoulder',.6,.3),('left_hip',.44,.55),('right_hip',.56,.55),('left_elbow',.32,.44),('left_wrist',.27,.56),('left_knee',.43,.74),('left_ankle',.42,.92)]}
    result=summarize_character(points,[1000,1500],'anime',pose='unknown')
    assert result['proportions']['shoulder_width_to_torso']['value']==pytest.approx(.5333333)
    assert result['proportions']['left_upper_arm_to_torso']['scope']=='projected_2d_ratio'
    assert result['symmetry_automatic_allowed'] is False
    assert result['regions']['hair']['status']=='unknown'
    assert result['regions']['clothing']['status']=='unknown'
    points['left_shoulder']['visibility']=.2
    result=summarize_character(points,[1000,1500],'anime')
    assert 'shoulder_width_to_torso' not in result['proportions']
    assert 'left_shoulder' in result['uncertain_landmarks']


def test_manual_corrections_are_not_claimed_as_model_detection_confidence():
    from backend.character_understanding import validate_landmarks,summarize_character
    points={'nose':{'x':.5,'y':.2,'source':'manual','reviewed':True}}
    validated=validate_landmarks(points)
    assert validated['nose']['visibility'] is None
    assert summarize_character(validated,[100,100],'nonhuman')['anatomy_constraints_enforced'] is False
    with pytest.raises(ValueError):validate_landmarks({'nose':{'x':1.2,'y':.2}})


def test_empty_detector_output_is_uncertain_not_a_fabricated_skeleton():
    from backend.character_understanding import summarize_character
    result=summarize_character({},[640,480],'cartoon')
    assert result['proportions']=={} and result['reliable_landmarks']==[]
    assert result['status']=='needs_manual_review'
