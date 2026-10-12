import numpy as np
import torch
import trimesh

def test_cpu_density_surface_faces_point_outward_after_upstream_axis_conversion():
    from backend.isosurface import cpu_marching_cubes
    n=32
    grid=np.stack(np.meshgrid(*[np.linspace(-1,1,n)]*3,indexing='ij'),axis=-1)
    density=0.6-np.linalg.norm(grid,axis=-1) # actual helper receives positive inside
    vertices,faces=cpu_marching_cubes(torch.tensor(density,dtype=torch.float32),0.0)
    # MarchingCubeHelper swaps the adapter's axes back into grid xyz.
    mesh=trimesh.Trimesh(vertices.numpy()[:,[2,1,0]],faces.numpy(),process=False)
    assert mesh.is_watertight and mesh.is_winding_consistent
    assert mesh.volume>0
    center=mesh.vertices.mean(axis=0)
    assert np.mean(np.einsum('ij,ij->i',mesh.triangles_center-center,mesh.face_normals)>0)>0.99

def test_integrity_reports_inside_out_closed_shell_even_with_finite_normals():
    from backend.mesh_quality import inspect_mesh
    mesh=trimesh.creation.icosphere(subdivisions=1)
    good=inspect_mesh(mesh.vertices,mesh.faces,normals=mesh.vertex_normals)
    bad=inspect_mesh(mesh.vertices,mesh.faces[:,::-1],normals=-mesh.vertex_normals)
    assert good['orientation']=='outward_closed' and good['signed_volume']>0
    assert bad['orientation']=='inward_closed' and bad['signed_volume']<0
    assert bad['watertight'] and bad['normals_finite']

def test_open_surface_is_not_falsely_called_outward_solid():
    from backend.mesh_quality import inspect_mesh
    result=inspect_mesh([[0,0,0],[1,0,0],[0,1,0]],[[0,1,2]])
    assert result['orientation']=='open_or_nonmanifold'
