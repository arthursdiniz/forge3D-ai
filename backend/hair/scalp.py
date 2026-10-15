"""Head-local anchoring surface, never the full character bounding-box top."""
import numpy as np

def estimate_scalp(scene,camera,face_box):
    import trimesh
    from backend.character_quality import canonical_vertices
    l,t,r,b=face_box;fw=r-l;fh=b-t
    if fw<=.005 or fh<=.005:raise ValueError('Head/face region too small for a safe scalp.')
    positions=camera.buffers[0];rows,cols=np.indices(positions.shape[:2]);x=(cols+.5)/camera.size;y=(rows+.5)/camera.size
    selected=(positions[...,3]>.5)&(x>=l)&(x<=r)&(y>=t)&(y<=b)
    visible=positions[selected,:3]
    if len(visible)<24:return {'status':'unsafe_original_retained','reason':'No sufficient local face/head surface in selected region.'}
    frame=camera.frame;scale=frame['scale'];center=np.asarray(frame['center'],float).copy()
    center[0]+=((l+r)/2-.5)/scale;center[1]+=(.5-(t+b)/2+fh*.24)/scale
    rx=fw/(2*scale)*1.1;ry=fh/(2*scale)*1.25
    points=[]
    for node in scene.graph.nodes_geometry:
        transform,name=scene.graph[node];points.append(canonical_vertices(trimesh.transform_points(scene.geometry[name].vertices,transform),camera.axis))
    points=np.vstack(points);local=(np.abs(points[:,0]-center[0])<rx*1.3)&(np.abs(points[:,1]-center[1])<ry*1.1)
    if local.sum()<24:return {'status':'unsafe_original_retained','reason':'Selected head has too few mesh samples.'}
    z_low,z_high=np.percentile(points[local,2],[2,98]);center[2]=(z_low+z_high)/2;rz=float(np.clip((z_high-z_low)/2,rx*.55,rx*1.1))
    return {'status':'reviewable','center':center.tolist(),'radii':[float(rx),float(ry),rz],'head_samples':int(local.sum()),'visible_face_samples':len(visible),'face_box':list(face_box),'method':'Head-local face projection and mesh depth samples; ellipsoidal anchoring hypothesis','estimated_not_anatomical_truth':True,'root_contact_allowed':True,'confidence':'reviewable; hidden scalp inferred'}

def scalp_sdf(points,scalp):
    center=np.asarray(scalp['center']);radii=np.asarray(scalp['radii']);return (np.linalg.norm((np.asarray(points)-center)/radii,axis=-1)-1)*radii.min()
