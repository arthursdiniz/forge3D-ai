"""Measured projected and geometric diagnostics; no invented identity score."""
import numpy as np

def silhouette_metrics(candidate,target):
    from scipy.ndimage import binary_erosion,distance_transform_edt
    if target is None:return {'status':'not_measurable','reason':'No reviewed/observed comparison mask; no ground-truth claim.'}
    a=np.asarray(candidate,bool);b=np.asarray(target,bool)
    if a.shape!=b.shape:raise ValueError('Silhouette masks must share a calibrated frame.')
    if not a.any() or not b.any():return {'status':'not_measurable','reason':'An empty mask cannot establish hair correspondence.'}
    ea=a&~binary_erosion(a);eb=b&~binary_erosion(b);distance=(distance_transform_edt(~eb)[ea].mean()+distance_transform_edt(~ea)[eb].mean())/2
    return {'status':'measured','iou':round(float((a&b).sum()/(a|b).sum()),6),'mean_contour_distance_pixels':round(float(distance),4),'reference_pixels':int(b.sum()),'candidate_pixels':int(a.sum()),'scope':'Observed/projected mask agreement with stated camera; not universal hair fidelity or automatic ground truth.'}

def mesh_integrity(mesh):
    area=np.asarray(mesh.area_faces);normals=np.asarray(mesh.vertex_normals)
    return {'triangles':len(mesh.faces),'finite':bool(np.isfinite(mesh.vertices).all() and np.isfinite(normals).all()),'degenerate_triangles':int((area<max(mesh.scale,1e-6)**2*1e-12).sum()),'watertight':bool(mesh.is_watertight),'winding_consistent':bool(mesh.is_winding_consistent),'volume':float(abs(mesh.volume)),'components':len(mesh.split(only_watertight=False)),'uv_valid':bool(getattr(mesh.visual,'uv',None) is not None and np.isfinite(mesh.visual.uv).all() and np.all((mesh.visual.uv>=0)&(mesh.visual.uv<=1)))}

def choose_refinement(candidates,before,occlusion_limit):
    baseline_distance=before.get('mean_contour_distance_pixels',np.inf)
    if not np.isfinite(baseline_distance):return None
    safe=[i for i,item in enumerate(candidates) if item['occlusion']<=occlusion_limit and item['metrics'].get('iou',-1)>=before.get('iou',0)-.001 and np.isfinite(item['metrics'].get('mean_contour_distance_pixels',np.inf)) and item['metrics']['mean_contour_distance_pixels']<=baseline_distance+.0001]
    return min(safe,key=lambda i:(candidates[i]['metrics']['mean_contour_distance_pixels'],-candidates[i]['metrics']['iou'])) if safe else None

def exported_mass_integrity(mesh):
    welded=mesh.copy();welded.merge_vertices(merge_tex=True,merge_norm=True)
    return {'uv_seams_welded_for_topology_only':True,'uv_valid':bool(getattr(mesh.visual,'uv',None) is not None and np.isfinite(mesh.visual.uv).all()),'geometric_topology':mesh_integrity(welded),'authored_normals_finite':bool(np.isfinite(mesh.vertex_normals).all())}
