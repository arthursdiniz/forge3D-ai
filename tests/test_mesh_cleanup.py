import numpy as np

def test_cleanup_removes_noise_without_erasing_small_intentional_parts_or_uv_seams():
    from backend.mesh_cleanup import cleanup_face_mask
    # Main triangle, a disconnected but long/thin accessory, a tiny speck,
    # a seam duplicate sharing positions, plus a degenerate/duplicate face.
    vertices=np.array([[0,0,0],[1,0,0],[0,1,0],
                       [2,0,0],[2.2,0,0],[2,0.001,0],
                       [3,0,0],[3.0001,0,0],[3,0.0001,0],
                       [0,0,0],[1,0,0],[0,0,1]],float)
    faces=np.array([[0,1,2],[3,4,5],[6,7,8],[9,11,10],[0,0,1],[2,1,0]])
    mask,report=cleanup_face_mask(vertices,faces)
    assert mask.tolist()==[True,True,False,True,False,False]
    assert report['removed_fragments']==1
    assert report['removed_degenerate_faces']==1
    assert report['removed_duplicate_faces']==1
    assert np.array_equal(vertices,np.array([[0,0,0],[1,0,0],[0,1,0],[2,0,0],[2.2,0,0],[2,0.001,0],[3,0,0],[3.0001,0,0],[3,0.0001,0],[0,0,0],[1,0,0],[0,0,1]],float))

def test_cleanup_keeps_the_only_component_even_when_it_is_tiny():
    from backend.mesh_cleanup import cleanup_face_mask
    mask,report=cleanup_face_mask(np.array([[0,0,0],[1e-5,0,0],[0,1e-5,0]]),np.array([[0,1,2]]))
    assert mask.tolist()==[True]
    assert report['removed_fragments']==0
