import numpy as np,pytest
from backend.character_base_mesh import body_parameters,create_body_mesh

def interpretation():
    points={'head_top':(.5,.08),'chin':(.5,.22),'left_shoulder':(.36,.29),'right_shoulder':(.64,.29),'left_hip':(.43,.52),'right_hip':(.57,.52),'left_elbow':(.29,.41),'right_elbow':(.71,.41),'left_wrist':(.25,.55),'right_wrist':(.75,.55),'left_knee':(.43,.71),'right_knee':(.57,.71),'left_ankle':(.43,.9),'right_ankle':(.57,.9)}
    return {'reviewed':True,'category':'anime','view':'front','pose':'a_pose','image_size':[600,1000],'landmarks':{name:{'x':x,'y':y,'source':'manual','reviewed':True,'visibility':None,'presence':None} for name,(x,y) in points.items()}}

def test_template_requires_reviewed_visible_joints_and_explicit_head_height():
    value=interpretation();value['landmarks'].pop('chin')
    with pytest.raises(ValueError,match='chin'):body_parameters(value)
    value=interpretation();value['reviewed']=False
    with pytest.raises(ValueError,match='revise'):body_parameters(value)

def test_anime_head_and_body_proportions_are_measured_and_volume_is_actual():
    value=interpretation();parameters=body_parameters(value)
    expected=(.22-.08)/(.52-.29)
    assert parameters['head_height']/parameters['torso_height']==pytest.approx(expected)
    mesh,report=create_body_mesh(parameters,resolution=48)
    assert mesh.is_watertight and mesh.is_winding_consistent and mesh.volume>0
    assert report['neural_generation'] is False and report['rig_ready'] is False
    assert report['template_origin']=='Forge3D own procedural body template'
    assert report['unobserved_depth']=='assumed; not recovered from the reference'
