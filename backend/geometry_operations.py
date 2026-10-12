"""Reversible edits with explicit regions and topology/volume/silhouette guards."""
import argparse,json,sys,time,hashlib
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))

def canonical_matrix(up_axis,front_axis):
    matrix=np.eye(4)
    if up_axis=='Z':matrix[:3,:3]=[[1,0,0],[0,0,1],[0,-1,0]]
    elif up_axis!='Y':raise ValueError('Eixo vertical inválido.')
    if front_axis=='x':
        rotation=np.eye(4);rotation[:3,:3]=[[0,0,-1],[0,1,0],[1,0,0]];matrix=rotation@matrix
    return matrix

def conservative_edit(scene,options,interpretation=None,reference=None,up_axis='Y',front_axis='negative_y'):
    import trimesh
    from backend.geometry_integrity import inspect_geometry,optional_surface_probes
    from backend.symmetry_correction import correct_symmetry
    from backend.sculpt_refinement import refine_surface
    from backend.refine_mesh import ensure_normals
    operation=options['operation'];interpretation=interpretation or {}
    if operation=='symmetry' and options.get('symmetry_mode','off')=='off':return scene.copy(),{'accepted':False,'reason':'Simetria Off preserva o original.','faces_changed':0}
    if operation=='symmetry' and (not options.get('symmetry_confirmed') or interpretation.get('pose') not in ['a_pose','t_pose','neutral'] or interpretation.get('view')!='front'):
        raise ValueError('Confirme pose frontal neutra/A-pose/T-pose e plano; pose dinâmica/desconhecida não admite simetria automática.')
    boxes=[]
    if options.get('region_bounds'):boxes.append(options['region_bounds'])
    for name in options.get('symmetry_regions',[]):
        region=interpretation.get('regions',{}).get(name,{})
        if region.get('bounds'):boxes.append(region['bounds'])
    if not boxes:raise ValueError('Selecione uma região explícita/revisada; não aplicar correção global.')
    protected=list(options.get('protected_bounds',[]))
    for name in ['hair','clothing','accessories']:
        region=interpretation.get('regions',{}).get(name,{})
        if region.get('bounds') and name not in options.get('symmetry_regions',[]):protected.append(region['bounds'])
    matrix=canonical_matrix(up_axis,front_axis);inverse=np.linalg.inv(matrix)
    original=scene.copy();working=scene.copy();working.apply_transform(matrix)
    combined=working.to_geometry();points=np.asarray(combined.vertices)
    lower=points.min(axis=0);upper=points.max(axis=0);height=max(upper[1]-lower[1],1e-8)
    frame=None
    if reference is not None:
        from backend.reference_texture import projection_frame,image_coordinates
        frame=projection_frame(points,np.asarray(reference))
    def selection(vertices):
        if frame:
            xy=image_coordinates(vertices,frame)/[frame['width'],frame['height']]
        else:xy=np.column_stack([(vertices[:,0]-lower[0])/max(upper[0]-lower[0],1e-8),(upper[1]-vertices[:,1])/height])
        def inside(box):
            a,b,c,d=box;return (xy[:,0]>=a)&(xy[:,0]<=c)&(xy[:,1]>=b)&(xy[:,1]<=d)
        chosen=np.zeros(len(vertices),bool)
        for box in boxes:chosen|=inside(box)
        for box in protected:chosen&=~inside(box)
        return chosen
    reports=[]
    # Material/UVs are copied per actual geometry instance before applying world edits.
    result=trimesh.Scene()
    for index,node in enumerate(working.graph.nodes_geometry):
        transform,name=working.graph[node];mesh=working.geometry[name].copy();mesh.apply_transform(transform)
        before=np.array(mesh.vertices,copy=True);normals=np.array(mesh.vertex_normals,copy=True);chosen=selection(before)
        if operation=='symmetry':
            edited,report=correct_symmetry(before,chosen,options.get('symmetry_mode','off'),options.get('symmetry_strength',.2),options.get('plane_yaw_degrees',0),options.get('plane_offset_ratio',0)*height,max_displacement_ratio=min(options.get('max_displacement_ratio',.003),.003),normals=normals)
        elif operation=='sculpt_refine':edited,report=refine_surface(before,mesh.faces,chosen,options.get('sculpt_strength',.1),options.get('sculpt_iterations',2))
        else:raise ValueError('Operação seletiva inválida.')
        mesh.vertices=edited
        if report.get('accepted'):ensure_normals(mesh,normals)
        reports.append(report);result.add_geometry(mesh,node_name=str(node),geom_name=f'{name}_{index}')
    after_mesh=result.to_geometry();before_report=inspect_geometry(combined.vertices,combined.faces);after_report=inspect_geometry(after_mesh.vertices,after_mesh.faces)
    failures=[]
    for key in ['boundary_edges','nonmanifold_edges','duplicate_faces','inconsistent_winding_edges','degenerate_triangles']:
        if after_report[key]>before_report[key]:failures.append(key)
    before_probes=optional_surface_probes(combined.vertices,combined.faces);after_probes=optional_surface_probes(after_mesh.vertices,after_mesh.faces)
    before_report['checks'].update(before_probes);after_report['checks'].update(after_probes)
    before_intersections=before_probes['intersections'].get('selected_faces');after_intersections=after_probes['intersections'].get('selected_faces')
    if before_intersections is not None and after_intersections is not None and after_intersections>before_intersections:failures.append('new_self_intersections')
    before_volume=abs(before_report['signed_volume']);after_volume=abs(after_report['signed_volume'])
    if before_report['watertight'] and before_volume>1e-9 and abs(after_volume/before_volume-1)>.01:failures.append('volume_change_above_1_percent')
    if len(before_report['components'])==len(after_report['components']):
        for before_shell,after_shell in zip(before_report['components'],after_report['components']):
            volume=abs(before_shell['signed_volume'])
            if before_shell['closed'] and volume>1e-9 and abs(abs(after_shell['signed_volume'])/volume-1)>.01:failures.append('shell_volume_change_above_1_percent')
    silhouette=None
    if reference is not None:
        from backend.character_quality import silhouette_measurement
        pre=silhouette_measurement(combined.vertices,combined.faces,np.asarray(reference));post=silhouette_measurement(after_mesh.vertices,after_mesh.faces,np.asarray(reference))
        silhouette={'before':pre,'after':post}
        if pre.get('iou') is not None and post.get('iou',0)<pre['iou']-.002:failures.append('front_silhouette_regression')
    accepted=any(report.get('accepted') for report in reports) and not failures
    report={'accepted':accepted,'operation':operation,'regions':boxes,'protected_regions':protected,'parts':reports,'before':before_report,'after':after_report,'rollback_reasons':failures,'silhouette':silhouette,'faces_changed':0,'uv_corners_preserved':True,'scope':'Selected bounded surface correction, not learned anatomical reconstruction.'}
    if not accepted:return original,report
    result.apply_transform(inverse);return result,report

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--input',required=True);parser.add_argument('--output',required=True);parser.add_argument('--options',required=True);parser.add_argument('--interpretation');parser.add_argument('--reference');parser.add_argument('--front-axis',default='negative_y');args=parser.parse_args()
    import trimesh
    from PIL import Image
    from backend.config import atomic_json
    directory=Path(args.output).resolve();directory.mkdir(parents=True,exist_ok=True);source=Path(args.input).resolve()
    if source==directory/'model.glb' or (directory/'model.glb').exists():raise ValueError('Preserve source; write a new version.')
    started=time.perf_counter();options=json.loads(Path(args.options).read_text(encoding='utf-8-sig'))
    interpretation=json.loads(Path(args.interpretation).read_text(encoding='utf-8')) if args.interpretation else None
    reference=Image.open(args.reference).convert('RGBA') if args.reference else None
    scene,report=conservative_edit(trimesh.load(source,force='scene',process=False),options,interpretation,reference,front_axis=args.front_axis)
    scene.export(directory/'model.glb',include_normals=True);report.update(seconds=round(time.perf_counter()-started,3),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest())
    atomic_json(directory/'geometry_operation.json',report)
if __name__=='__main__':main()
