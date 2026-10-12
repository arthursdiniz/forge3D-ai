import numpy as np,trimesh,pytest
from backend.geometry_operations import conservative_edit

def test_off_is_exact_and_does_not_change_uv_faces_or_protected_vertices():
    mesh=trimesh.creation.icosphere(subdivisions=2)
    mesh.visual=trimesh.visual.TextureVisuals(uv=np.zeros((len(mesh.vertices),2)))
    scene=trimesh.Scene(mesh)
    result,report=conservative_edit(scene,{'operation':'symmetry','symmetry_mode':'off'},up_axis='Y')
    edited=next(iter(result.geometry.values()))
    assert np.array_equal(edited.vertices,mesh.vertices) and np.array_equal(edited.faces,mesh.faces)
    assert np.array_equal(edited.visual.uv,mesh.visual.uv)
    assert report['accepted'] is False

def test_dynamic_pose_is_not_forced_into_symmetry_even_when_checkbox_is_confirmed():
    scene=trimesh.Scene(trimesh.creation.icosphere())
    with pytest.raises(ValueError,match='pose'):
        conservative_edit(scene,{'operation':'symmetry','symmetry_mode':'soft','symmetry_confirmed':True,'symmetry_regions':['torso']},interpretation={'pose':'dynamic','view':'front','regions':{'torso':{'bounds':[.3,.3,.7,.7]}}},up_axis='Y')

def test_manual_bounds_produce_bounded_edit_and_preserve_uvs_and_shell_volume():
    mesh=trimesh.creation.icosphere(subdivisions=2)
    points=mesh.vertices.copy();points[points[:,0]>0,0]*=1.01;mesh.vertices=points
    uv=np.column_stack([(points[:,0]+1)/2,(points[:,1]+1)/2]);mesh.visual=trimesh.visual.TextureVisuals(uv=uv)
    options={'operation':'symmetry','symmetry_mode':'soft','symmetry_confirmed':True,'symmetry_regions':['torso']}
    result,report=conservative_edit(trimesh.Scene(mesh),options,interpretation={'pose':'a_pose','view':'front','regions':{'torso':{'bounds':[0,0,1,1]}}},up_axis='Y')
    assert report['accepted'] is True
    edited=next(iter(result.geometry.values()))
    assert np.array_equal(edited.visual.uv,uv) and np.array_equal(edited.faces,mesh.faces)
    assert np.linalg.norm(edited.vertices-points,axis=1).max()<=.006001

def test_micro_requires_explicit_region_and_does_not_smooth_whole_object():
    with pytest.raises(ValueError,match='região'):
        conservative_edit(trimesh.Scene(trimesh.creation.icosphere()),{'operation':'sculpt_refine'},up_axis='Y')
