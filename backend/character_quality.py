"""Character comparison with explicit camera, confidence and measurement limits."""
import numpy as np


def view_vertices(vertices,view='front'):
    result=np.array(vertices,dtype=np.float64,copy=True)
    if view=='left':result[:,0]=-np.asarray(vertices)[:,2];result[:,2]=np.asarray(vertices)[:,0]
    elif view=='right':result[:,0]=np.asarray(vertices)[:,2];result[:,2]=-np.asarray(vertices)[:,0]
    elif view=='back':result[:,0]*=-1;result[:,2]*=-1
    elif view!='front':raise ValueError('Vista anatômica desconhecida.')
    return result


def canonical_vertices(vertices,front_axis='negative_y'):
    return view_vertices(vertices,'left') if front_axis=='x' else np.array(vertices,copy=True)


def compare_proportions(reference,candidate):
    if reference.get('view')!='front' or candidate.get('view')!='front':return {'status':'NOT_MEASURABLE','reason':'Comparable frontal views have not been confirmed.','anatomy_score':None,'measurements':{}}
    measurements={}
    for name,before in reference.get('proportions',{}).items():
        after=candidate.get('proportions',{}).get(name)
        if after and before['value']>1e-8:
            measurements[name]={'reference':before['value'],'candidate':after['value'],'relative_difference':round((after['value']-before['value'])/before['value'],6),'scope':'projected_2d_ratio','interpretation':'Camera, pose and landmark uncertainty affect the measurement; no realistic anatomy target imposed.'}
    return {'status':'MEASURED' if measurements else 'NOT_MEASURABLE','measurements':measurements,'anatomy_score':None,'scope':'Reliable 2D landmark relations only; not 3D anatomy, identity or rig readiness.'}


def silhouette_measurement(vertices,faces,rgba,view='front',resolution=256):
    from scipy.ndimage import zoom
    from .reference_texture import projection_frame,rasterize_front
    rgba=np.asarray(rgba)
    if rgba.ndim!=3 or rgba.shape[-1]!=4 or rgba[...,3].min()==255:
        return {'status':'NOT_MEASURABLE','reason':'A real foreground mask is required; opaque background was not called object silhouette.'}
    foreground=rgba[...,3]>128
    if not foreground.any():return {'status':'NOT_MEASURABLE','reason':'No confident foreground mask.'}
    points=view_vertices(vertices,view);frame=projection_frame(points,rgba)
    raster=rasterize_front(points,faces,frame,resolution)
    predicted=np.flipud(raster[...,3]>.5)
    target=zoom(foreground.astype(np.uint8),(resolution/foreground.shape[0],resolution/foreground.shape[1]),order=0).astype(bool)
    union=np.logical_or(predicted,target).sum()
    return {'status':'MEASURED','iou':round(float(np.logical_and(predicted,target).sum()/max(union,1)),6),'view':view,'raster_resolution':resolution,'method':'Height-aligned estimated orthographic camera and alpha foreground overlap','scope':'2D silhouette overlap only; inferred depth and anatomy are not scored','camera_assumption':'Canonical front+Z/Y-up; references in matching pose and labeled view.'}


def analyze_character(scene,interpretation=None,candidate_pose=None,references=None,front_axis='negative_y',surface_probes=False):
    from .geometry_integrity import inspect_geometry,optional_surface_probes
    mesh=scene.to_geometry();vertices=canonical_vertices(mesh.vertices,front_axis)
    integrity=inspect_geometry(mesh.vertices,mesh.faces,mesh.visual.uv if hasattr(mesh.visual,'uv') else None,mesh.vertex_normals)
    if surface_probes:integrity['checks'].update(optional_surface_probes(mesh.vertices,mesh.faces))
    silhouettes={}
    for view,image in (references or {}).items():
        if view in ['front','left','right','back']:silhouettes[view]=silhouette_measurement(vertices,mesh.faces,np.asarray(image),view)
    return {'integrity':integrity,'silhouettes':silhouettes,'proportions':compare_proportions(interpretation or {},candidate_pose or {}),'semantic_conditioning':False,'automatic_candidate_selection':False,'rig_ready':False,'observed_views':list((references or {}).keys()),'inferred_geometry':'All unobserved directions remain model estimates.','limitations':['No learned face/finger anatomical correction.','Components/intersections can be intentional; diagnostics do not automatically fuse or fill geometry.']}


class CharacterQualityAnalyzer:
    analyze=staticmethod(analyze_character)
