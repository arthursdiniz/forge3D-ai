"""Non-mutating geometric/UV measurements, never perceptual quality scores."""
import numpy as np

def inspect_mesh(vertices,faces,uv=None,normals=None,tolerance=1e-7):
    vertices=np.asarray(vertices,dtype=np.float64)
    faces=np.asarray(faces,dtype=np.int64)
    if not len(faces) or not np.isfinite(vertices).all():raise ValueError('Empty/nonfinite mesh.')
    if np.any(faces<0) or np.any(faces>=len(vertices)):raise ValueError('Invalid face index.')
    points=vertices[faces]
    area=np.linalg.norm(np.cross(points[:,1]-points[:,0],points[:,2]-points[:,0]),axis=1)*0.5
    area_tolerance=max(float(np.ptp(vertices,axis=0).max())**2*1e-12,1e-16)
    # Inspect welded positions only; original vertices, UV seams and normals stay intact.
    unique,inverse=np.unique(np.rint(vertices/tolerance).astype(np.int64),axis=0,return_inverse=True)
    triangles=inverse[faces]
    edges=np.sort(np.concatenate([triangles[:,[0,1]],triangles[:,[1,2]],triangles[:,[2,0]]]),axis=1)
    edges=edges[edges[:,0]!=edges[:,1]]
    edges,counts=np.unique(edges,axis=0,return_counts=True)
    parents=np.arange(len(unique))
    def find(index):
        while parents[index]!=index:
            parents[index]=parents[parents[index]];index=parents[index]
        return index
    for a,b in edges:
        a=find(a);b=find(b)
        if a!=b:parents[max(a,b)]=min(a,b)
    while not np.array_equal(parents,parents[parents]):parents=parents[parents]
    roots,component_counts=np.unique(parents[triangles[:,0]],return_counts=True)
    component_counts=sorted(component_counts.tolist(),reverse=True)
    result={'finite_vertices':True,'degenerate_triangles':int((area<=area_tolerance).sum()),'area_tolerance':area_tolerance,'surface_area':float(area.sum()),'connected_components':len(roots),'component_triangle_counts':component_counts,'welded_vertices':len(unique),'inspection_weld_tolerance':tolerance,'boundary_edges':int((counts==1).sum()),'nonmanifold_edges':int((counts>2).sum()),'watertight':bool(np.all(counts==2)),'automatic_cleanup':False}
    centered=points-(vertices.min(axis=0)+vertices.max(axis=0))/2
    signed_volume=float(np.einsum('ij,ij->i',centered[:,0],np.cross(centered[:,1],centered[:,2])).sum()/6)
    result['signed_volume']=signed_volume
    result['orientation']=('outward_closed' if signed_volume>0 else 'inward_closed') if result['watertight'] else 'open_or_nonmanifold'
    if uv is not None:
        uv=np.asarray(uv)
        result.update(uv_finite=bool(np.isfinite(uv).all()),uv_outside_unit_square=int(np.any((uv<0)|(uv>1),axis=-1).sum()))
    if normals is not None:
        normals=np.asarray(normals)
        result.update(normals_finite=bool(np.isfinite(normals).all()),zero_normals=int((np.linalg.norm(normals,axis=-1)<1e-6).sum()))
    return result
