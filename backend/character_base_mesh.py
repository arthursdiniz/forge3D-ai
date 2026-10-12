"""Own experimental body template fitted to reviewed 2D joints; no AI fallback."""
import argparse,json,sys,time,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
REQUIRED=['head_top','chin','left_shoulder','right_shoulder','left_hip','right_hip','left_elbow','right_elbow','left_wrist','right_wrist','left_knee','right_knee','left_ankle','right_ankle']

def validate_reviewed_body(interpretation):
    from backend.character_understanding import validate_landmarks,trusted
    if not interpretation.get('reviewed'):raise ValueError('Primeiro revise e salve a interpretação do corpo.')
    if interpretation.get('category') in ['nonhuman','custom']:raise ValueError('Template atual é humanoide; categorias não humanas exigem template próprio.')
    if interpretation.get('view')!='front':raise ValueError('Template inicial exige vista frontal revisada; profundidade não é recuperada.')
    points=validate_landmarks(interpretation.get('landmarks',{}))
    missing=[name for name in REQUIRED if name not in points or not trusted(points[name])]
    if missing:raise ValueError('Landmarks revisados/confiáveis ausentes: '+', '.join(missing))
    return points

def body_parameters(interpretation):
    import numpy as np
    from backend.character_understanding import trusted
    points=validate_reviewed_body(interpretation)
    width,height=interpretation['image_size'];top=points['head_top']['y'];bottom=max(points['left_ankle']['y'],points['right_ankle']['y'])
    if bottom-top<.25:raise ValueError('Referência não contém corpo frontal suficiente para o template.')
    scale=2/((bottom-top)*height);center=(points['left_hip']['x']+points['right_hip']['x'])/2
    joints={name:np.array([(point['x']-center)*width*scale,(bottom-point['y'])*height*scale,0.]) for name,point in points.items() if trusted(point)}
    head_height=float(np.linalg.norm(joints['head_top']-joints['chin']))
    shoulders=(joints['left_shoulder']+joints['right_shoulder'])/2;hips=(joints['left_hip']+joints['right_hip'])/2
    torso_height=float(np.linalg.norm(shoulders-hips));shoulder_width=float(np.linalg.norm(joints['left_shoulder']-joints['right_shoulder']));hip_width=float(np.linalg.norm(joints['left_hip']-joints['right_hip']))
    if min(head_height,torso_height,shoulder_width,hip_width)<.02:raise ValueError('Relações degeneradas; revise os landmarks.')
    head_width=float(np.linalg.norm(joints['left_ear']-joints['right_ear'])) if all(name in joints for name in ['left_ear','right_ear']) else head_height*.8
    return {'joints':{name:point.tolist() for name,point in joints.items()},'head_height':head_height,'head_width':head_width,'torso_height':torso_height,'shoulder_width':shoulder_width,'hip_width':hip_width,'category':interpretation.get('category'),'depth_policy':'assumed proportional thickness; no learned or observed depth','missing_semantics':['facial identity','hair','clothing','accessories','fingers','rig']}

def create_body_mesh(parameters,resolution=128):
    import numpy as np
    import trimesh
    from skimage.measure import marching_cubes
    if not 32<=resolution<=160:raise ValueError('Template extraction resolution outside validated CPU bounds.')
    joints={name:np.asarray(point,dtype=float) for name,point in parameters['joints'].items()}
    head_height=parameters['head_height'];shoulder_width=parameters['shoulder_width'];hip_width=parameters['hip_width']
    shoulder=(joints['left_shoulder']+joints['right_shoulder'])/2;hips=(joints['left_hip']+joints['right_hip'])/2
    parts=[]
    def capsule(a,b,r):parts.append(('capsule',np.asarray(a),np.asarray(b),float(r)))
    def ellipsoid(center,radii):parts.append(('ellipsoid',np.asarray(center),np.asarray(radii)))
    head=(joints['head_top']+joints['chin'])/2
    ellipsoid(head,[parameters['head_width']/2,head_height/2,parameters['head_width']*.4])
    capsule(joints['chin'],shoulder,shoulder_width*.115)
    ellipsoid((shoulder+hips)/2,[shoulder_width*.48,parameters['torso_height']*.66,shoulder_width*.25])
    ellipsoid(hips,[hip_width*.58,parameters['torso_height']*.2,shoulder_width*.25])
    for side in ['left','right']:
        radius=shoulder_width*.11
        capsule(joints[side+'_shoulder'],joints[side+'_elbow'],radius)
        capsule(joints[side+'_elbow'],joints[side+'_wrist'],radius*.8)
        ellipsoid(joints[side+'_wrist']+[0,-radius*.4,0],[radius*.75,radius*1.25,radius*.6])
        capsule(joints[side+'_hip'],joints[side+'_knee'],hip_width*.27)
        capsule(joints[side+'_knee'],joints[side+'_ankle'],hip_width*.22)
        ellipsoid(joints[side+'_ankle']+[0,-hip_width*.13,hip_width*.14],[hip_width*.24,hip_width*.17,hip_width*.48])
    all_points=np.array(list(joints.values()));padding=max(head_height,shoulder_width)*.65
    lower=all_points.min(axis=0)-padding;upper=all_points.max(axis=0)+padding
    spacing=float((upper-lower).max()/(resolution-1));shape=np.ceil((upper-lower)/spacing).astype(int)+1
    grids=np.meshgrid(*(lower[i]+np.arange(shape[i])*spacing for i in range(3)),indexing='ij');points=np.stack(grids,axis=-1).astype(np.float32)
    field=np.full(tuple(shape),np.inf,np.float32)
    for part in parts:
        if part[0]=='capsule':
            _,a,b,radius=part;delta=b-a;t=np.clip(np.sum((points-a)*delta,axis=-1)/max(float(delta@delta),1e-12),0,1)
            distance=np.linalg.norm(points-a-t[...,None]*delta,axis=-1)-radius
        else:
            _,center,radii=part;distance=(np.linalg.norm((points-center)/radii,axis=-1)-1)*radii.min()
        np.minimum(field,distance,out=field)
    vertices,faces,normals,values=marching_cubes(field,level=0,spacing=(spacing,)*3)
    mesh=trimesh.Trimesh(vertices=vertices+lower,faces=faces,process=True)
    if mesh.volume<0:mesh.invert()
    if not mesh.is_watertight or not mesh.is_winding_consistent:raise RuntimeError('Template extraction failed volume/integrity checks; no fallback.')
    report={'template_origin':'Forge3D own procedural body template','license':'CC0-1.0 own procedural template','neural_generation':False,'strategy':'experimental reviewed-joint body scaffold','rig_ready':False,'unobserved_depth':'assumed; not recovered from the reference','resolution':resolution,'triangles':len(mesh.faces),'parameters':parameters,'missing_semantics':parameters['missing_semantics'],'warnings':['Corpo assistido experimental, sem identidade facial, roupa, cabelo ou rig.','Ajuste usa relações 2D revisadas; não reconstrói profundidade/verso a partir de uma imagem.','Template é uma base editável e não substitui um candidato neural fiel.']}
    return mesh,report

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--image',required=True);parser.add_argument('--output',required=True);parser.add_argument('--options',required=True);args=parser.parse_args()
    from PIL import Image
    from backend.config import atomic_json
    from backend.mesh_quality import inspect_mesh
    directory=Path(args.output).resolve();directory.mkdir(parents=True,exist_ok=True)
    if (directory/'original.glb').exists():raise ValueError('Preserve prior template generation.')
    interpretation=json.loads((directory/'character_interpretation.json').read_text(encoding='utf-8'));started=time.perf_counter()
    mesh,report=create_body_mesh(body_parameters(interpretation));mesh.export(directory/'original.glb',include_normals=True);mesh.export(directory/'raw_generation.glb',include_normals=True)
    image=Image.open(args.image).convert('RGBA')
    if interpretation.get('reference_transform'):image=image.crop(interpretation['reference_transform']['crop_pixels'])
    image.save(directory/'prepared_masked.png');image.save(directory/'prepared_alpha.png');image.thumbnail((512,512));image.save(directory/'prepared.png')
    prep={'method':'reviewed original landmarks, no neural encoder','warnings':report['warnings'],'background_action':'preserved_alpha' if image.getchannel('A').getextrema()[0]<255 else 'kept'}
    metadata={**report,'provider':'character_base_mesh','coordinate_system':'y_up','render_front_axis':'negative_y','vertices':len(mesh.vertices),'dimensions':mesh.extents.tolist(),'texture':{'method':'none','generated':False},'effective_settings':{'mc_resolution':128,'texture_resolution':None},'image_preparation':prep,'peak_vram_mb':0,'peak_reserved_mb':0,'total_seconds':round(time.perf_counter()-started,2),'inference_seconds':0,'offline_network_blocked':True,'integrity':[inspect_mesh(mesh.vertices,mesh.faces,normals=mesh.vertex_normals)],'source_sha256':hashlib.sha256(Path(args.image).read_bytes()).hexdigest()}
    atomic_json(directory/'base_mesh.json',report);atomic_json(directory/'inference.json',metadata);atomic_json(directory/'preparation.json',prep)
if __name__=='__main__':main()
