"""Measured topology checks with per-shell orientation and optional CPU probes."""
import time
import numpy as np
from .mesh_quality import inspect_mesh


def welded_topology(vertices,faces,tolerance=1e-7):
    vertices=np.asarray(vertices,dtype=np.float64);faces=np.asarray(faces,dtype=np.int64)
    _,indices,inverse=np.unique(np.rint(vertices/tolerance).astype(np.int64),axis=0,return_index=True,return_inverse=True)
    return vertices[indices],inverse[faces]


def inspect_geometry(vertices,faces,uv=None,normals=None,intentional_open=False):
    started=time.perf_counter();report=inspect_mesh(vertices,faces,uv,normals)
    points,triangles=welded_topology(vertices,faces)
    canonical=np.sort(triangles,axis=1)
    _,counts=np.unique(canonical,axis=0,return_counts=True)
    duplicates=int(np.sum(counts-1))
    directed=np.concatenate([triangles[:,[0,1]],triangles[:,[1,2]],triangles[:,[2,0]]])
    directed=directed[directed[:,0]!=directed[:,1]]
    edges=np.sort(directed,axis=1);unique,inverse,edge_counts=np.unique(edges,axis=0,return_inverse=True,return_counts=True)
    signs=np.where(directed[:,0]<directed[:,1],1,-1);orientation_sum=np.bincount(inverse,weights=signs,minlength=len(unique))
    inconsistent=int(((edge_counts==2)&(np.abs(orientation_sum)>0)).sum())
    parents=np.arange(len(points))
    def find(index):
        while parents[index]!=index:parents[index]=parents[parents[index]];index=parents[index]
        return index
    for a,b in unique:
        a=find(a);b=find(b)
        if a!=b:parents[max(a,b)]=min(a,b)
    while not np.array_equal(parents,parents[parents]):parents=parents[parents]
    face_components=parents[triangles[:,0]]
    components=[]
    for identifier in np.unique(face_components):
        selected=triangles[face_components==identifier]
        corner=points[selected];area=np.linalg.norm(np.cross(corner[:,1]-corner[:,0],corner[:,2]-corner[:,0]),axis=1).sum()/2
        lower=corner.min(axis=(0,1));upper=corner.max(axis=(0,1));centered=corner-(lower+upper)/2
        volume=float(np.einsum('ij,ij->i',centered[:,0],np.cross(centered[:,1],centered[:,2])).sum()/6)
        component_edges=np.sort(np.concatenate([selected[:,[0,1]],selected[:,[1,2]],selected[:,[2,0]]]),axis=1);component_edges=component_edges[component_edges[:,0]!=component_edges[:,1]]
        _,component_counts=np.unique(component_edges,axis=0,return_counts=True)
        closed=bool(np.all(component_counts==2))
        components.append({'triangles':len(selected),'area':float(area),'dimensions':(upper-lower).tolist(),'signed_volume':volume,'closed':closed,'orientation':('outward_closed' if volume>0 else 'inward_closed') if closed else 'open_or_nonmanifold','intent':'unknown; semantic part identity is not inferred'})
    components.sort(key=lambda item:item['triangles'],reverse=True)
    orientation='inconsistent' if inconsistent else ('mixed_shell_orientation' if any(item['orientation']=='inward_closed' for item in components) else report['orientation'])
    checks={'closed_surface':{'status':'INFO' if intentional_open else ('PASS' if report['watertight'] else 'WARN'),'value':report['watertight'],'interpretation':'Open surfaces may be intentional; no automatic hole filling.'},'winding':{'status':'WARN' if inconsistent else 'PASS','value':inconsistent,'method':'directed edges of welded inspection topology'},'duplicate_faces':{'status':'WARN' if duplicates else 'PASS','value':duplicates,'method':'identical unordered welded corner indices'},'intersections':{'status':'NOT_TESTED','reason':'Optional geometric intersection probe was not requested.'},'thin_regions':{'status':'NOT_TESTED','reason':'Optional inward-ray sampling was not requested.'}}
    return {**report,'duplicate_faces':duplicates,'inconsistent_winding_edges':inconsistent,'orientation_status':orientation,'components':components,'surface_policy':'intentional_open' if intentional_open else 'unspecified','checks':checks,'automatic_repair':False,'seconds':round(time.perf_counter()-started,3)}


def optional_surface_probes(vertices,faces,sample_count=64):
    """Actual self-intersection selection and bounded inward ray lengths."""
    checks={}
    points,triangles=welded_topology(vertices,faces)
    try:
        import pymeshlab
        mesh=pymeshlab.Mesh(vertex_matrix=points,face_matrix=triangles.astype(np.int32))
        meshset=pymeshlab.MeshSet();meshset.add_mesh(mesh)
        meshset.apply_filter('compute_selection_by_self_intersections_per_face')
        count=int(meshset.current_mesh().face_selection_array().sum())
        checks['intersections']={'status':'WARN' if count else 'PASS','selected_faces':count,'method':'MeshLab geometric self-intersection face selection','interpretation':'Intersections can be intentional overlapping clothes/parts; face selection is not an anatomical defect classification.'}
    except (ImportError,RuntimeError,ValueError) as error:checks['intersections']={'status':'NOT_TESTED','reason':str(error)[:300]}
    try:
        import trimesh
        mesh=trimesh.Trimesh(vertices=points,faces=triangles,process=False)
        if not mesh.is_watertight or not mesh.is_winding_consistent:
            checks['thin_regions']={'status':'NOT_MEASURABLE','reason':'Inward ray lengths need consistent closed surfaces; open surface thickness was not inferred.'}
        else:
            indices=np.linspace(0,len(mesh.faces)-1,min(sample_count,len(mesh.faces)),dtype=int)
            epsilon=max(mesh.extents.max()*1e-5,1e-8)
            origins=mesh.triangles_center[indices]-mesh.face_normals[indices]*epsilon
            locations,rays,hit_faces=mesh.ray.intersects_location(origins,-mesh.face_normals[indices],multiple_hits=False)
            lengths=np.linalg.norm(locations-origins[rays],axis=1)
            valid=lengths>epsilon*2;lengths=lengths[valid]
            threshold=float(mesh.extents.max()*.003)
            checks['thin_regions']={'status':'WARN' if len(lengths) and np.any(lengths<threshold) else 'PASS','sample_count':len(indices),'successful_rays':int(valid.sum()),'min_sampled_length':float(lengths.min()) if len(lengths) else None,'below_threshold':int((lengths<threshold).sum()),'threshold':threshold,'method':'Deterministic inward triangle-center ray sampling; bounded64rays','interpretation':'Sampled interior chords only; not exhaustive wall thickness and not proof of missing body volume.'}
            if not len(lengths):checks['thin_regions'].update(status='NOT_MEASURABLE',reason='No usable inward-ray chord was observed; empty samples do not validate thickness.')
    except (ImportError,RuntimeError,ValueError) as error:checks['thin_regions']={'status':'NOT_TESTED','reason':str(error)[:300]}
    return checks


class GeometryIntegrity:
    inspect=staticmethod(inspect_geometry)
    probes=staticmethod(optional_surface_probes)
