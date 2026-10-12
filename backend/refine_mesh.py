"""Reversible local mesh refinement; original input is never overwritten."""
import argparse,json,sys,time,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))

def ensure_normals(mesh,fallback=None):
    import numpy as np
    from scipy.spatial import cKDTree
    positions=np.asarray(mesh.vertices)
    faces=np.asarray(mesh.faces)
    # Group only for shading, never for topology/UV. Original normal directions
    # distinguish hard edges while copies introduced by UV seams share a group.
    keys=np.rint(positions/1e-7).astype(np.int64)
    if fallback is not None:keys=np.column_stack([keys,np.rint(np.asarray(fallback)*1e4).astype(np.int64)])
    _,groups=np.unique(keys,axis=0,return_inverse=True)
    corners=positions[faces]
    face_normals=np.cross(corners[:,1]-corners[:,0],corners[:,2]-corners[:,0])
    face_normals/=np.maximum(np.linalg.norm(face_normals,axis=1,keepdims=True),1e-30)
    accumulated=np.zeros((int(groups.max())+1,3))
    for corner in range(3):
        a=corners[:,(corner+1)%3]-corners[:,corner];b=corners[:,(corner+2)%3]-corners[:,corner]
        angles=np.arctan2(np.linalg.norm(np.cross(a,b),axis=1),(a*b).sum(axis=1))
        np.add.at(accumulated,groups[faces[:,corner]],face_normals*angles[:,None])
    normals=accumulated[groups]
    valid=np.isfinite(normals).all(axis=1)&(np.linalg.norm(normals,axis=1)>1e-8)
    if fallback is not None:
        old=np.asarray(fallback);usable=~valid & np.isfinite(old).all(axis=1)&(np.linalg.norm(old,axis=1)>1e-8)
        normals[usable]=old[usable];valid|=usable
    if not valid.all():
        if not valid.any():raise ValueError('No valid surface normal; preserve original and report failure.')
        _,nearest=cKDTree(mesh.vertices[valid]).query(mesh.vertices[~valid])
        normals[~valid]=normals[valid][nearest]
    normals/=np.linalg.norm(normals,axis=1,keepdims=True)
    mesh.vertex_normals=normals

def cleanup_mesh(mesh,options):
    import numpy as np
    from backend.mesh_cleanup import cleanup_face_mask
    old_normals=np.array(mesh.vertex_normals,copy=True)
    mask,measured=cleanup_face_mask(mesh.vertices,mesh.faces,options.get('max_fragment_faces',32),options.get('max_fragment_extent',0.006))
    mesh.update_faces(mask)
    surviving=np.unique(mesh.faces.reshape(-1))
    mesh.remove_unreferenced_vertices()
    ensure_normals(mesh,old_normals[surviving])
    return measured

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--input',required=True);parser.add_argument('--output',required=True);parser.add_argument('--options',required=True);parser.add_argument('--source');parser.add_argument('--generation-options');args=parser.parse_args()
    import numpy as np,trimesh
    from PIL import Image
    from backend.preprocess import prepare_image
    from backend.mesh_cleanup import cleanup_face_mask
    from backend.silhouette_refinement import refine_silhouette
    options=json.loads(Path(args.options).read_text(encoding='utf-8-sig'));operation=options['operation']
    directory=Path(args.output);directory.mkdir(parents=True,exist_ok=True)
    target=directory/'model.glb'
    if Path(args.input).resolve()==target.resolve():raise ValueError('Refinement must write a new version.')
    original_hash=hashlib.sha256(Path(args.input).read_bytes()).hexdigest()
    started=time.perf_counter();scene=trimesh.load(args.input,force='scene',process=False)
    before=sum(len(mesh.faces) for mesh in scene.geometry.values())
    report={'operation':operation,'input_sha256':original_hash,'before_triangles':before}
    if operation=='cleanup':
        reports=[]
        for mesh in scene.geometry.values():
            reports.append(cleanup_mesh(mesh,options))
        report['meshes']=reports
    elif operation=='refine_silhouette':
        if len(scene.geometry)!=1 or len(scene.graph.nodes_geometry)!=1:raise ValueError('Silhouette refinement currently supports a single generated mesh.')
        parameters=json.loads(Path(args.generation_options).read_text(encoding='utf-8-sig'))
        preparation=prepare_image(Path(args.source),directory/'reference_prepared.png',foreground_ratio=parameters.get('foreground_ratio') or 5/6,crop=parameters.get('crop'),background_mode=parameters.get('background_mode') or 'auto',preparation_preset=parameters.get('preparation_preset','prop'),remove_background=parameters.get('remove_background',False),model_dir=ROOT/'models/rembg',background_color=(255,255,255),save_alpha=True)
        if preparation['background_action']=='kept':raise ValueError('Refinamento exige máscara do objeto: use alpha ou remoção de fundo na geração.')
        rgba=np.asarray(Image.open(directory/'reference_prepared_alpha.png').convert('RGBA'))
        node=scene.graph.nodes_geometry[0];matrix,name=scene.graph[node];mesh=scene.geometry[name]
        world=trimesh.transform_points(mesh.vertices,matrix)
        output,measured=refine_silhouette(world,mesh.faces,rgba,options.get('refinement_strength',0.65),options.get('max_displacement_ratio',0.03))
        if measured['accepted']:
            old_normals=np.array(mesh.vertex_normals,copy=True)
            mesh.vertices=trimesh.transform_points(output,np.linalg.inv(matrix));ensure_normals(mesh,old_normals)
        report.update(refinement=measured,reference_preparation=preparation)
    else:raise ValueError('Unsupported refinement operation.')
    temporary=directory/'model.refining.glb';scene.export(temporary,file_type='glb',include_normals=True);temporary.replace(target)
    assert hashlib.sha256(Path(args.input).read_bytes()).hexdigest()==original_hash
    report.update(after_triangles=sum(len(mesh.faces) for mesh in scene.geometry.values()),seconds=round(time.perf_counter()-started,2),original_preserved=True)
    (directory/'refinement.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('REAL_MESH_REFINEMENT '+json.dumps(report),flush=True)
if __name__=='__main__':main()
