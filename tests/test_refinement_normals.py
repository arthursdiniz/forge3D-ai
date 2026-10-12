import numpy as np
import trimesh

def test_refinement_keeps_finite_unit_normals_at_degenerate_vertices():
    from backend.refine_mesh import ensure_normals
    mesh=trimesh.Trimesh(vertices=[[0,0,0],[1,0,0],[0,1,0],[2,0,0],[3,0,0]],faces=[[0,1,2],[0,3,4]],process=False)
    ensure_normals(mesh,fallback=np.tile([0,0,1],(5,1)))
    assert np.isfinite(mesh.vertex_normals).all()
    assert np.allclose(np.linalg.norm(mesh.vertex_normals,axis=1),1)

def test_uv_seam_duplicates_keep_equal_smooth_normals_after_geometry_changes():
    from backend.refine_mesh import ensure_normals
    vertices=np.array([[0,0,0],[1,0,0],[0,1,0],[0,0,0],[0,1,0],[-1,0,0]],float)
    mesh=trimesh.Trimesh(vertices=vertices,faces=[[0,1,2],[3,4,5]],process=False)
    original=np.tile([0,0,1],(6,1))
    mesh.vertices[5,2]=0.3
    ensure_normals(mesh,original)
    assert np.allclose(mesh.vertex_normals[0],mesh.vertex_normals[3])
    assert np.allclose(mesh.vertex_normals[2],mesh.vertex_normals[4])

def test_original_hard_edge_normals_remain_separate_across_identical_positions():
    from backend.refine_mesh import ensure_normals
    mesh=trimesh.Trimesh(vertices=[[0,0,0],[1,0,0],[0,1,0],[0,0,0],[0,1,0],[0,0,1]],faces=[[0,1,2],[3,4,5]],process=False)
    ensure_normals(mesh,np.array([[0,0,1]]*3+[[1,0,0]]*3))
    assert not np.allclose(mesh.vertex_normals[0],mesh.vertex_normals[3])

def test_cleanup_remapping_keeps_original_smoothing_groups_after_removing_early_vertices():
    from backend.refine_mesh import cleanup_mesh
    mesh=trimesh.Trimesh(vertices=[[6,0,0],[6.0001,0,0],[6,0.0001,0],[0,0,0],[1,0,0],[0,1,0],[0,0,0],[0,1,0],[-1,0,0.3]],faces=[[0,1,2],[3,4,5],[6,7,8]],vertex_normals=np.tile([0,0,1],(9,1)),process=False)
    report=cleanup_mesh(mesh,{})
    assert report['removed_fragments']==1
    assert np.allclose(mesh.vertex_normals[0],mesh.vertex_normals[3])
    assert np.allclose(mesh.vertex_normals[2],mesh.vertex_normals[4])
