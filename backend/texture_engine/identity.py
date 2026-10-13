"""Compare oriented world triangles, including duplicated corners and instances."""
import numpy as np

def world_triangles(scene):
    import trimesh
    arrays=[]
    for node in scene.graph.nodes_geometry:
        matrix,name=scene.graph[node]
        mesh=scene.geometry[name]
        arrays.append(trimesh.transform_points(mesh.vertices,matrix)[mesh.faces])
    if not arrays:raise ValueError('No mesh triangles.')
    result=np.concatenate(arrays)
    if not np.isfinite(result).all():raise ValueError('Nonfinite world geometry.')
    return result

def compare_geometry(before,after):
    from collections import defaultdict,deque
    from scipy.spatial import cKDTree
    source=world_triangles(before);target=world_triangles(after)
    span=float(np.ptp(source.reshape(-1,3),axis=0).max())
    tolerance=max(span*1e-6,1e-8)
    report={'equivalent':False,'source_triangles':len(source),'result_triangles':len(target),'tolerance_world':tolerance,'winding_preserved':False,'method':'world triangle multiset; cyclic corner correspondence, unique matches, no reversed winding'}
    if len(source)!=len(target):return report
    def key(triangle):
        corners=np.rint(triangle/tolerance).astype(np.int64)
        return min(tuple(np.roll(corners,shift,axis=0).ravel()) for shift in range(3))
    def error(a,b):return min(float(np.abs(a-np.roll(b,shift,axis=0)).max()) for shift in range(3))
    # Exact/quantized duplicates are O(N), avoiding a quadratic list of all
    # coincident centroid neighbours. Only boundary rounding needs a KD lookup.
    buckets=defaultdict(deque);target_keys=[]
    for index,triangle in enumerate(target):
        signature=key(triangle);target_keys.append(signature);buckets[signature].append(index)
    used=np.zeros(len(target),bool);maximum=0.;tree=None;alternatives={}
    for triangle in source:
        signature=key(triangle);candidate=alternatives.get(signature,signature)
        if not buckets[candidate]:
            if tree is None:tree=cKDTree(target.mean(axis=1))
            candidate=None
            for index in tree.query_ball_point(triangle.mean(axis=0),tolerance):
                if not used[index] and error(triangle,target[index])<=tolerance:candidate=target_keys[index];break
            if candidate is None:return report
            alternatives[signature]=candidate
        index=buckets[candidate].popleft();difference=error(triangle,target[index])
        if difference>tolerance:return report
        used[index]=True;maximum=max(maximum,difference)
    report.update(equivalent=True,winding_preserved=True,max_corner_error=maximum,source_dimensions=np.ptp(source.reshape(-1,3),axis=0).tolist(),result_dimensions=np.ptp(target.reshape(-1,3),axis=0).tolist())
    return report
