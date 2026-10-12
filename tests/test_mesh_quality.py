import numpy as np
from backend.mesh_quality import inspect_mesh

def test_seam_duplicates_do_not_become_fake_components():
    vertices=np.array([[0,0,0],[1,0,0],[0,1,0],[0,0,0],[1,0,0],[0,0,1]],float)
    faces=np.array([[0,1,2],[3,5,4]])
    result=inspect_mesh(vertices,faces)
    assert result['connected_components']==1
    assert result['welded_vertices']==4
    assert result['nonmanifold_edges']==0
    assert result['boundary_edges']==4

def test_degenerate_faces_disconnected_parts_and_invalid_uv_are_reported():
    vertices=np.array([[0,0,0],[1,0,0],[0,1,0],[5,5,0],[6,5,0],[5,6,0]],float)
    result=inspect_mesh(vertices,np.array([[0,1,2],[3,4,5],[0,0,1]]),uv=np.array([[0,0],[np.nan,1]]))
    assert result['degenerate_triangles']==1
    assert result['connected_components']==2
    assert result['uv_finite'] is False
    assert result['component_triangle_counts']==[2,1]
