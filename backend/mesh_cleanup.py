"""Conservative face selection. Positions and per-loop UVs are never welded."""
import numpy as np

def cleanup_face_mask(vertices,faces,max_fragment_faces=32,max_fragment_extent=0.006):
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    v=np.asarray(vertices,dtype=np.float64);f=np.asarray(faces,dtype=np.int64)
    if f.ndim!=2 or f.shape[1]!=3 or not len(f) or not np.isfinite(v).all():raise ValueError('Cleanup requires finite nonempty triangular mesh.')
    if np.any(f<0) or np.any(f>=len(v)):raise ValueError('Invalid face indices.')
    if not 0<=max_fragment_faces<=32 or not 0<=max_fragment_extent<=0.006:raise ValueError('Conservative cleanup limits exceeded.')
    extent=float(np.ptp(v,axis=0).max())
    area=np.linalg.norm(np.cross(v[f[:,1]]-v[f[:,0]],v[f[:,2]]-v[f[:,0]]),axis=1)*0.5
    degenerate=area<=max(extent**2*1e-14,1e-30)
    _,welded=np.unique(np.rint(v/1e-7).astype(np.int64),axis=0,return_inverse=True)
    triangles=welded[f]
    _,first=np.unique(np.sort(triangles,axis=1),axis=0,return_index=True)
    duplicates=np.ones(len(f),bool);duplicates[first]=False
    duplicates&=~degenerate
    keep=~(degenerate|duplicates)
    selected=np.flatnonzero(keep)
    if not len(selected):raise ValueError('Cleanup would leave an empty mesh; original preserved.')
    edges=np.concatenate([triangles[keep][:,[0,1]],triangles[keep][:,[1,2]],triangles[keep][:,[2,0]]])
    graph=coo_matrix((np.ones(len(edges),np.uint8),(edges[:,0],edges[:,1])),shape=(len(np.unique(welded)),)*2)
    _,labels=connected_components(graph,directed=False)
    face_labels=labels[triangles[selected,0]]
    components,counts=np.unique(face_labels,return_counts=True)
    largest=components[np.argmax(counts)]
    removed_fragments=0;fragment_faces=0
    for component,count in zip(components,counts):
        if component==largest or count>max_fragment_faces:continue
        indices=selected[face_labels==component]
        part=v[f[indices].reshape(-1)]
        if float(np.ptp(part,axis=0).max())<=extent*max_fragment_extent:
            keep[indices]=False;removed_fragments+=1;fragment_faces+=len(indices)
    return keep,{'removed_degenerate_faces':int(degenerate.sum()),'removed_duplicate_faces':int(duplicates.sum()),'removed_fragments':removed_fragments,'removed_fragment_faces':fragment_faces,'before_faces':len(f),'after_faces':int(keep.sum()),'max_fragment_faces':max_fragment_faces,'max_fragment_extent_ratio':max_fragment_extent,'positions_welded':False,'uv_seams_preserved':True}
