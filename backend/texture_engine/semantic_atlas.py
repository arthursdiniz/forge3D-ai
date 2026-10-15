"""Reusable material/owner-bound samples and actual calibrated view inputs."""
from pathlib import Path
import numpy as np
from PIL import Image
from .region_camera import RegionCamera
from .semantic_projection import project_semantic
from .semantic_fusion import fuse_semantic
from ..character_quality import canonical_vertices

YAW={'front':0,'back':180,'left':90,'right':-90}

def load_views(scene,analysis):
    from .texture_fusion import gradient_reference
    folder=Path(analysis['directory']);result=[]
    for name,record in analysis['views'].items():
        if name not in YAW:raise ValueError('Unsupported semantic view.')
        path=folder/'views'/name;rgba=np.asarray(Image.open(path/'source.png').convert('RGBA'));source=np.asarray(Image.open(path/'source_labels.png'));target=np.asarray(Image.open(path/'target_labels.png'));origin=np.asarray(Image.open(path/'source_origin.png'))
        camera=RegionCamera(scene,analysis.get('front_axis','negative_y'),target.shape[0],record['camera_frame'],YAW[name])
        if source.shape!=rgba.shape[:2] or origin.shape!=source.shape or target.shape!=(camera.size,camera.size):raise ValueError('Semantic reference/camera dimensions changed.')
        result.append({'name':name,'camera':camera,'rgba':rgba,'source_labels':source,'target_labels':target,'source_origin':origin,'registration':record['registration'],'gradient':gradient_reference(rgba)[...,0].astype('f4')/255})
    if not result:raise ValueError('No registered semantic views.')
    return result

def atlas_geometry(mesh,matrix,axis):
    import trimesh
    from ..neural_texture import rasterize_positions
    from .uv import inspect_uv
    material=getattr(mesh.visual,'material',None);image=getattr(material,'baseColorTexture',None)
    if not isinstance(material,trimesh.visual.material.PBRMaterial) or image is None:raise ValueError('Semantic editing needs an existing PBR albedo and UVs; texturize globally first.')
    width,height=image.size
    if max(width,height)>4096:raise ValueError('Semantic atlas limit4096; source retained.')
    uv=inspect_uv(mesh)
    if not uv['valid'] or uv['overlap_percent']>.5:raise ValueError('Semantic editing needs preserved valid UVs without significant overlap.')
    world=canonical_vertices(trimesh.transform_points(mesh.vertices,matrix),axis);normals=canonical_vertices(np.asarray(mesh.vertex_normals)@np.linalg.inv(matrix[:3,:3]),axis);normals/=np.maximum(np.linalg.norm(normals,axis=1,keepdims=True),1e-12)
    positions=rasterize_positions(world,mesh.faces,mesh.visual.uv,(width,height),face_ids=True);vectors=rasterize_positions(normals,mesh.faces,mesh.visual.uv,(width,height));occupied=positions[...,3]>.5;points=positions[occupied,:3];directions=vectors[occupied,:3];directions/=np.maximum(np.linalg.norm(directions,axis=1,keepdims=True),1e-12);faces=positions[occupied,3]
    components=trimesh.graph.connected_component_labels(mesh.face_adjacency,node_count=len(mesh.faces));components=components[np.clip(faces.astype(int)-1,0,len(mesh.faces)-1)]
    return {'points':points,'normals':directions,'faces':faces,'occupied':occupied,'components':components,'uv':uv}

def atlas_observations(samples,views,owner,classes=None,protected_classes=None):
    from .semantic_taxonomy import CLASS_IDS
    count=len(samples['points']);rgb=np.zeros((count,3),'f4');weight=np.zeros(count,'f4');labels=np.zeros(count,'u1');target=np.zeros(count,'u1');origin=np.zeros(count,'u1');source_view=np.zeros(count,'u1');protected_region=np.zeros(count,bool);blocked=0;conflicts=0
    selected=[CLASS_IDS[value] for value in classes] if classes else None;protected=[CLASS_IDS[value] for value in protected_classes or []]
    for start in range(0,count,131072):
        stop=min(start+131072,count);section=slice(start,stop);items=[]
        for view in views:
            item=project_semantic(view['camera'],samples['points'][section],samples['normals'][section],view['rgba'],view['source_labels'],view['target_labels'],view['registration'],owner,samples['faces'][section],view['source_origin'],view.get('gradient'));blocked+=int(item['conflict'].sum())
            if selected is not None:item['weight'][~np.isin(item['source_class'],selected)]=0
            item['weight'][np.isin(item['target_class'],protected)]=0;items.append(item)
        protected_region[section]=np.stack([i['protected']|(i['target_visible']&np.isin(i['target_class'],protected))|(i['visible']&np.isin(i['source_class'],protected)) for i in items],axis=1).any(axis=1);weights=np.stack([i['weight'] for i in items],axis=1);weights[protected_region[section]]=0;result=fuse_semantic(np.stack([i['rgb'] for i in items],axis=1),weights,np.stack([i['gradient'] for i in items],axis=1),np.stack([i['source_class'] for i in items],axis=1));winner=np.argmax(weights,axis=1);rows=np.arange(stop-start)
        rgb[section]=result['rgb'];weight[section]=result['confidence'];labels[section]=result['class'];source_view[section]=result['source_view'];origin[section]=np.stack([i['origin'] for i in items],axis=1)[rows,winner]
        # Preserve independently observed target class even where source projection was blocked.
        evidence=np.stack([i['target_class'] for i in items],axis=1);visible=np.stack([i['target_visible'] for i in items],axis=1);target_winner=np.argmax(visible*(evidence>1),axis=1);target[section]=evidence[rows,target_winner];target[section][~(visible&(evidence>1)).any(axis=1)]=0;conflicts+=int(result['semantic_conflict'].sum())
    return {'rgb':rgb,'weight':weight,'class':labels,'target_class':target,'origin':origin,'source_view':source_view,'blocked':blocked,'conflicts':conflicts,'protected':protected_region}

def write_analysis_atlas(scene,analysis,directory):
    from .semantic_masks import PALETTE
    views=load_views(scene,analysis);records=[]
    for owner,node in enumerate(scene.graph.nodes_geometry,1):
        matrix,name=scene.graph[node];mesh=scene.geometry[name];samples=atlas_geometry(mesh,matrix,analysis['front_axis']);observed=atlas_observations(samples,views,owner);mask=samples['occupied'];labels=np.zeros(mask.shape,'u1');labels[mask]=np.where(observed['weight']>0,observed['class'],observed['target_class']);origin=np.zeros_like(labels);origin[mask]=np.where(observed['weight']>0,np.where(observed['origin']==2,2,1),0);folder=Path(directory)/'atlas'/f'{owner-1:03d}';folder.mkdir(parents=True,exist_ok=True)
        Image.fromarray(labels[::-1]).save(folder/'Labels.png');Image.fromarray(PALETTE[labels[::-1]]).save(folder/'Preview.png');Image.fromarray(origin[::-1]).save(folder/'Origin.png');face_classes={}
        for value in np.unique(labels[mask]):face_classes[str(int(value))]=int((labels[mask]==value).sum())
        face_labels=np.zeros(len(mesh.faces),'u1')
        for value in np.unique(labels[mask]):
            if value<=1:continue
            selected=(labels[mask]==value)&(observed['weight']>0);faces=samples['faces'][selected].astype(int)-1;counts=np.bincount(faces,minlength=len(mesh.faces));face_labels[(counts>0)&(face_labels==0)]=value
        np.save(folder/'FaceLabels.npy',face_labels,allow_pickle=False)
        records.append({'node':node,'geometry':name,'material':mesh.visual.material.name,'labels':f'atlas/{owner-1:03d}/Labels.png','preview':f'atlas/{owner-1:03d}/Preview.png','origin':f'atlas/{owner-1:03d}/Origin.png','face_labels':f'atlas/{owner-1:03d}/FaceLabels.npy','class_texels':face_classes,'observed_texels':int((observed['weight']>0).sum()),'blocked_cross_class':observed['blocked'],'scope':'Reviewed visible projection/target inference; hidden surfaces unknown; per-face labels are observed texel summaries.'})
    return records
