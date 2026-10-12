import numpy as np
import trimesh


def test_only_matching_uv_boundary_edges_are_reconnected_without_moving_surface():
    from backend.topology_seams import reconnect_uv_seams
    sphere=trimesh.creation.icosphere(subdivisions=1)
    vertices=sphere.vertices[sphere.faces].reshape(-1,3)
    normals=sphere.vertex_normals[sphere.faces].reshape(-1,3)
    faces=np.arange(len(vertices)).reshape(-1,3)
    result,triangles,new_normals,report=reconnect_uv_seams(vertices,faces,normals,np.zeros(len(faces),int))
    restored=trimesh.Trimesh(result,triangles,process=False)
    assert restored.is_watertight and restored.is_winding_consistent
    assert np.array_equal(result[triangles],vertices[faces])
    assert len(triangles)==len(faces) and report['vertices_reconnected']>0
    assert len(result)==len(sphere.vertices)


def test_coincident_overlapping_shells_are_not_merged():
    from backend.topology_seams import reconnect_uv_seams
    sphere=trimesh.creation.icosphere(subdivisions=0)
    vertices=np.tile(sphere.vertices[sphere.faces].reshape(-1,3),(2,1))
    normals=np.tile(sphere.vertex_normals[sphere.faces].reshape(-1,3),(2,1))
    faces=np.arange(len(vertices)).reshape(-1,3)
    result,triangles,new_normals,report=reconnect_uv_seams(vertices,faces,normals,np.zeros(len(faces),int))
    assert report['vertices_reconnected']==0
    assert np.array_equal(result,vertices) and np.array_equal(triangles,faces)


def test_different_material_regions_and_sharp_normals_are_protected():
    from backend.topology_seams import reconnect_uv_seams
    vertices=np.array([[0,0,0],[1,0,0],[0,1,0],[1,0,0],[0,0,0],[1,-1,0]],float)
    faces=np.arange(6).reshape(-1,3);normals=np.tile([0,0,1.],(6,1))
    assert reconnect_uv_seams(vertices,faces,normals,[0,1])[3]['vertices_reconnected']==0
    normals[3:]=[0,1,0]
    assert reconnect_uv_seams(vertices,faces,normals,[0,0])[3]['vertices_reconnected']==0
