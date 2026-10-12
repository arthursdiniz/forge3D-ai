import numpy as np


def test_soft_symmetry_improves_mutual_pairs_with_bounded_movement_and_protected_vertices():
    from backend.symmetry_correction import correct_symmetry
    left=np.array([[-.4,0,0],[-.4,.3,0],[-.4,.6,0],[-.4,.9,0]])
    right=np.array([[.42,0,0],[.42,.3,0],[.42,.6,0],[.42,.9,0]])
    vertices=np.vstack([left,right,[[.7,1.2,.1]]])
    selected=np.ones(len(vertices),bool);selected[-1]=False
    result,report=correct_symmetry(vertices,selected=selected,mode='soft',strength=.3,max_displacement_ratio=.01)
    assert report['accepted'] and report['paired_vertices']==8
    assert report['pair_distance_after']<report['pair_distance_before']
    assert report['max_displacement']<=1.2*.01+1e-9
    assert np.array_equal(result[-1],vertices[-1])


def test_nonzero_local_plane_is_used_and_missing_correspondence_is_not_forced():
    from backend.symmetry_correction import correct_symmetry
    vertices=np.array([[.1,0,0],[.9,0,0],[.1,1,0],[.9,1,0]])
    result,report=correct_symmetry(vertices,plane_offset=.5,mode='soft')
    assert np.allclose(result,vertices)
    assert report['plane']['offset']==.5
    dynamic=np.array([[-.4,0,0],[-.4,.3,0],[.4,1,0],[.4,1.3,0]])
    result,report=correct_symmetry(dynamic,mode='strong',match_distance_ratio=.03)
    assert report['accepted'] is False and np.array_equal(result,dynamic)


def test_off_preserves_intentional_asymmetry_exactly():
    from backend.symmetry_correction import correct_symmetry
    vertices=np.array([[-.2,0,0],[.3,1,0],[.8,.5,.2]])
    result,report=correct_symmetry(vertices,mode='off')
    assert np.array_equal(result,vertices) and report['mode']=='off'
