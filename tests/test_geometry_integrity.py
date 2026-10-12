import numpy as np

def test_zero_successful_thickness_rays_are_not_reported_as_a_pass(monkeypatch):
    import trimesh
    from backend.geometry_integrity import optional_surface_probes
    monkeypatch.setattr('trimesh.ray.ray_triangle.RayMeshIntersector.intersects_location',lambda *args,**kwargs:(np.empty((0,3)),np.array([],dtype=int),np.array([],dtype=int)))
    mesh=trimesh.creation.icosphere(subdivisions=1)
    report=optional_surface_probes(mesh.vertices,mesh.faces)
    assert report['thin_regions']['successful_rays']==0
    assert report['thin_regions']['status']=='NOT_MEASURABLE'
import trimesh


def test_integrity_detects_duplicate_faces_and_inconsistent_winding():
    from backend.geometry_integrity import inspect_geometry
    box=trimesh.creation.box()
    broken=box.faces.copy();broken[0]=broken[0,::-1]
    report=inspect_geometry(box.vertices,broken)
    assert report['inconsistent_winding_edges']>0
    assert report['orientation_status']=='inconsistent'
    duplicated=np.vstack([box.faces,box.faces[0]])
    report=inspect_geometry(box.vertices,duplicated)
    assert report['duplicate_faces']==1


def test_open_surface_is_not_automatically_repaired_or_called_a_hole_defect():
    from backend.geometry_integrity import inspect_geometry
    report=inspect_geometry([[0,0,0],[1,0,0],[0,1,0]],[[0,1,2]],intentional_open=True)
    assert report['boundary_edges']==3
    assert report['surface_policy']=='intentional_open'
    assert report['checks']['closed_surface']['status']=='INFO'
    assert report['automatic_repair'] is False


def test_components_have_per_shell_orientation_instead_of_only_global_volume():
    from backend.geometry_integrity import inspect_geometry
    first=trimesh.creation.box();second=trimesh.creation.box();second.apply_translation([3,0,0])
    mesh=trimesh.util.concatenate([first,trimesh.Trimesh(vertices=second.vertices,faces=second.faces[:,::-1],process=False)])
    report=inspect_geometry(mesh.vertices,mesh.faces)
    assert report['connected_components']==2
    assert sorted(item['orientation'] for item in report['components'])==['inward_closed','outward_closed']
