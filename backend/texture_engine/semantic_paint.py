"""Immutable semantic Reference Fidelity with measured protected pixels/channels."""
import copy,json,time
from pathlib import Path
import numpy as np
from PIL import Image
from .semantic_atlas import load_views,atlas_geometry,atlas_observations
from .semantic_taxonomy import CLASS_IDS,CLASS_NAMES,FACIAL_IDS
from .semantic_fusion import surface_fill,semantic_seams
from .texture_fusion import srgb_to_linear,linear_to_srgb

def completion_allowed(observed,target,generated,protected):
    from .semantic_projection import semantic_allowed
    allowed=~np.asarray(observed)&~np.asarray(protected)&semantic_allowed(generated,target,True)
    facial=np.isin(generated,list(FACIAL_IDS));allowed&=~facial|np.isin(target,list(FACIAL_IDS))
    return allowed

def sample_generated_labels(controls,view,points,labels):
    from .semantic_projection import sample_labels
    native=controls.native((points-controls.center)/controls.scale);matrix,_=controls.cameras[view];clip=np.column_stack([native,np.ones(len(native))])@matrix.T
    return sample_labels(labels,clip[:,:2]/2+.5)

def generated_head_crop(controls,view,scene,analysis):
    import trimesh
    from ..character_quality import canonical_vertices
    record=analysis['views'].get('front',{});box=record.get('target',{}).get('portrait_crop')
    if not box:return None
    points=np.concatenate([trimesh.transform_points(scene.geometry[scene.graph[node][1]].vertices,scene.graph[node][0]) for node in scene.graph.nodes_geometry]);points=canonical_vertices(points,analysis['front_axis']);frame=record['camera_frame'];xy=np.column_stack([.5+(points[:,0]-frame['center'][0])*frame['scale'],.5-(points[:,1]-frame['center'][1])*frame['scale']]);l,t,r,b=box;head=points[(xy[:,0]>=l)&(xy[:,0]<=r)&(xy[:,1]>=t)&(xy[:,1]<=b)]
    if len(head)<4:return None
    native=controls.native((head-controls.center)/controls.scale);matrix,_=controls.cameras[view];pixels=(np.column_stack([native,np.ones(len(native))])@matrix.T)[:,:2]/2+.5;low=np.clip(pixels.min(axis=0)-.02,0,1);high=np.clip(pixels.max(axis=0)+.02,0,1)
    return [float(low[0]),float(low[1]),float(high[0]),float(high[1])] if np.all(high-low>.025) else None

def canonical_camera_samples(camera):
    angle=np.deg2rad(-camera.yaw);c,s=np.cos(angle),np.sin(angle);inverse=np.array([[c,0,s],[0,1,0],[-s,0,c]])
    return camera.buffers[0][...,:3].reshape(-1,3)@inverse,camera.buffers[1][...,:3].reshape(-1,3)@inverse

def generated_views(scene,analysis,options,directory,root):
    from .neural import generate_views
    from .semantic_inference import segment_image
    image=Image.open(Path(analysis['directory'])/'views/front/source.png').convert('RGBA')
    if image.getchannel('A').getextrema()[0]==255:
        from rembg import remove,new_session
        import os
        if not (Path(root)/'models/rembg/u2netp.onnx').is_file():raise ValueError('Local background resource missing for neural completion.')
        os.environ['U2NET_HOME']=str(Path(root)/'models/rembg');image=remove(image,session=new_session('u2netp',providers=['CPUExecutionProvider']))
    settings={'conditioning':'image','front_axis':analysis['front_axis'],'prompt':options.get('prompt',''),'style':options.get('style','anime'),'seed':options.get('seed',44),'fidelity':1.}
    images,controls,metadata=generate_views(scene,{'front':np.asarray(image)},settings,directory);labels={}
    for name,rgba in images.items():labels[name]=segment_image(Image.fromarray(rgba),root,generated_head_crop(controls,name,scene,analysis),'anime',Path(directory)/'generated_semantics'/name)[0]
    return images,labels,controls,metadata

def paint_semantic(scene,analysis,options,directory,root,*,automatic_evidence=None):
    import trimesh
    from backend.hair.pipeline import preserved_copy
    from .identity import compare_geometry
    from .texture_seams import inspect_seams
    from .semantic_masks import PALETTE
    from ..character_quality import view_vertices
    started=time.perf_counter();directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    if not options.get('reviewed_alignment'):
        from ..workflows.alignment import validate_automatic_evidence
        validate_automatic_evidence(analysis,automatic_evidence)
    if (directory/'model.glb').exists():raise ValueError('Create a new semantic version; original outputs are immutable.')
    names=[scene.graph[n][1] for n in scene.graph.nodes_geometry]
    if len(set(names))!=len(names):raise ValueError('Shared instances need independent texture slots before semantic editing; original retained.')
    views=load_views(scene,analysis);result=preserved_copy(scene);records=[];total=observed_count=generated_count=filled_count=changed_count=blocked=0;all_preserved=True;neural=None;generated=None;protected_ids=[CLASS_IDS[n] for n in options.get('protected_classes',[])];selected_ids=[CLASS_IDS[n] for n in options.get('classes',['hair','face','eyes','mouth','clothes'])]
    if options.get('completion','preserve')=='neural':generated=generated_views(scene,analysis,options,directory,root);neural=generated[3]
    for owner,node in enumerate(scene.graph.nodes_geometry,1):
        matrix,name=scene.graph[node];mesh=scene.geometry[name];samples=atlas_geometry(mesh,matrix,analysis['front_axis']);data=atlas_observations(samples,views,owner,options.get('classes',['hair','face','eyes','mouth','clothes']),options.get('protected_classes',[]));occupied=samples['occupied'];material=mesh.visual.material;original=np.asarray(material.baseColorTexture.convert('RGBA'));before=original[::-1].copy();paint=before.copy();colors=data['rgb'].copy();observed=data['weight']>0;edit=observed.copy();class_map=np.where(observed,data['class'],data['target_class']).astype('u1');origin=np.where(observed,np.where(data['origin']==2,2,1),0).astype('u1');protected=np.isin(data['target_class'],protected_ids)|data['protected'];blocked+=data['blocked'];generated_mask=np.zeros(len(edit),bool)
        if options.get('surface_fill',False):
            allowed=np.isin(class_map,selected_ids)&~protected;seed=observed&allowed;candidate,filled=surface_fill(samples['points'],samples['normals'],colors,seed,np.where(allowed,class_map,0),samples['components'],max(mesh.scale,1e-8)*options.get('fill_radius',.01));colors[filled]=candidate[filled];edit|=filled;origin[filled]=3;filled_count+=int(filled.sum())
        if generated:
            images,labels,controls,_=generated;weights=np.zeros(len(edit))
            for view,rgba in images.items():
                rgb,weight=controls.project(view,samples['points'],samples['normals'],rgba)
                category=sample_generated_labels(controls,view,samples['points'],labels[view])
                allowed=completion_allowed(edit,data['target_class'],category,protected)&np.isin(category,selected_ids)&(weight>weights)
                colors[allowed]=rgb[allowed];class_map[allowed]=category[allowed];weights[allowed]=weight[allowed]
            generated_mask=weights>0;edit|=generated_mask;origin[generated_mask]=4;generated_count+=int(generated_mask.sum())
        protected|=~np.isin(class_map,selected_ids);edit&=~protected;origin[~edit]=0
        amount=np.zeros(occupied.shape,'f4');amount[occupied]=np.where(edit,options.get('intensity',1.),0)
        if options.get('feather_pixels',0):
            from scipy.ndimage import distance_transform_edt
            amount*=np.clip(distance_transform_edt(amount>0)/options['feather_pixels'],0,1)
        factor=np.asarray(material.baseColorFactor if material.baseColorFactor is not None else [255]*4,dtype=float)/255
        if np.any(factor[:3]<.01) and edit.any():raise ValueError('Albedo factor suppresses editable color; adjust it explicitly first.')
        if options.get('operation','reference')=='color_adjust':colors=np.clip(before[occupied,:3]/255*np.array(options.get('tint',[1,1,1])),0,1)
        else:colors=linear_to_srgb(np.clip(srgb_to_linear(colors)/np.maximum(factor[:3],.01),0,1))
        requested=before[occupied,:3]/255;amount_flat=amount[occupied];requested[edit]=linear_to_srgb(srgb_to_linear(requested[edit])*(1-amount_flat[edit,None])+srgb_to_linear(colors[edit])*amount_flat[edit,None]);paint[occupied,:3]=np.rint(np.clip(requested,0,1)*255).astype('u1');origin[edit&(amount_flat<.999)]+=4;output=paint[::-1].copy();mask=np.zeros(occupied.shape,bool);mask[occupied]=edit;mask=mask[::-1];classes=np.zeros(occupied.shape,'u1');classes[occupied]=class_map;classes=classes[::-1];seams_before=inspect_seams(mesh,output)
        if options.get('seam_correction',True):output=semantic_seams(mesh,output,mask,classes)
        preserved=np.array_equal(output[~mask],original[~mask]) and np.array_equal(output[...,3],original[...,3]);all_preserved&=preserved
        if not preserved:raise ValueError('Protected semantic pixels or alpha changed; original retained.')
        copied=copy.deepcopy(material);copied.baseColorTexture=Image.fromarray(output);result.geometry[name].visual.material=copied;folder=directory/'textures'/f'{owner-1:03d}';folder.mkdir(parents=True,exist_ok=True);Image.fromarray(output).save(folder/'Albedo.png');Image.fromarray(original).save(folder/'PreviousAlbedo.png');Image.fromarray(mask.astype('u1')*255).save(folder/'EditMask.png');Image.fromarray(classes).save(folder/'SemanticLabels.png');Image.fromarray(PALETTE[classes]).save(folder/'SemanticPreview.png');provenance=np.zeros(occupied.shape,'u1');provenance[occupied]=origin;Image.fromarray(provenance[::-1]).save(folder/'SemanticOrigin.png');Image.fromarray(np.rint(amount[::-1]*255).astype('u1')).save(folder/'BlendWeight.png');view_map=np.zeros(occupied.shape,'u1');view_map[occupied]=data['source_view'];Image.fromarray(view_map[::-1]).save(folder/'SourceView.png')
        maps={key:f'textures/{owner-1:03d}/{value}.png' for key,value in [('albedo','Albedo'),('previous_albedo','PreviousAlbedo'),('edit_mask','EditMask'),('semantic_labels','SemanticLabels'),('semantic_preview','SemanticPreview'),('semantic_origin','SemanticOrigin'),('source_view','SourceView'),('blend_weight','BlendWeight')]}
        for field,label in [('normalTexture','normal'),('occlusionTexture','occlusion'),('metallicRoughnessTexture','metallic_roughness'),('emissiveTexture','emissive')]:
            image=getattr(material,field,None)
            if image is not None:image.save(folder/(label+'.png'));maps[label]=f'textures/{owner-1:03d}/{label}.png'
        changed=int(np.any(output!=original,axis=2).sum());changed_count+=changed;total+=int(occupied.sum());observed_count+=int(observed.sum());records.append({'name':material.name,'geometry':name,'node':node,'maps':maps,'changed_pixels':changed,'protected_pixels_equal':bool(preserved),'coverage_percent':round(float(observed.mean()*100),2),'normal_preserved':material.normalTexture is not None,'seams':{'before':seams_before,'after':inspect_seams(mesh,output)},'atlas_size':list(material.baseColorTexture.size),'uv':{**samples['uv'],'created':False}})
    result.export(directory/'model.glb',include_normals=True);restored=trimesh.load(directory/'model.glb',force='scene',process=False);geometry=compare_geometry(scene,restored)
    if not geometry['equivalent']:raise ValueError('Semantic painting changed world geometry.')
    channels=[]
    for name,mesh in scene.geometry.items():
        after=restored.geometry[name];checks={'uv':np.allclose(mesh.visual.uv,after.visual.uv,atol=1e-6,rtol=0),'normals':np.allclose(mesh.vertex_normals,after.vertex_normals,atol=1e-6,rtol=0)}
        for field in ['normalTexture','occlusionTexture','metallicRoughnessTexture','emissiveTexture']:
            previous=getattr(mesh.visual.material,field,None);current=getattr(after.visual.material,field,None)
            if previous is not None:checks[field]=current is not None and np.array_equal(np.asarray(previous),np.asarray(current))
        if not all(checks.values()):raise ValueError('Protected UV/normals/data map changed on GLB roundtrip.')
        channels.append({'geometry':name,'preserved':{key:bool(value) for key,value in checks.items()}})
    frames={};metrics={}
    from .region_camera import RegionCamera
    from .texture_metrics import image_metrics
    from .semantic_projection import project_semantic
    for view in views:
        camera=view['camera'];after=RegionCamera(result,analysis['front_axis'],camera.size,camera.frame,camera.yaw);Image.fromarray(camera.image).save(directory/f'semantic_before_{view["name"]}.png');Image.fromarray(after.image).save(directory/f'semantic_after_{view["name"]}.png');points,normals=canonical_camera_samples(camera);target=project_semantic(camera,points,normals,view['rgba'],view['source_labels'],view['target_labels'],view['registration']);selected=(target['weight']>0)&np.isin(target['source_class'],selected_ids)&~np.isin(target['target_class'],protected_ids)&(camera.buffers[0][...,3].ravel()>.5);reference=np.dstack([target['rgb'].reshape(camera.size,camera.size,3)*255,np.full((camera.size,camera.size),255)]);metrics[view['name']]={'before':image_metrics(camera.image,reference,selected.reshape(camera.size,camera.size)),'after':image_metrics(after.image,reference,selected.reshape(camera.size,camera.size))}
    for name,yaw in [('left',90),('right',-90),('back',180)]:
        if name not in analysis['views']:
            for label,current in [('before',scene),('after',result)]:Image.fromarray(RegionCamera(current,analysis['front_axis'],512,yaw=yaw).image).save(directory/f'semantic_{label}_{name}.png')
    semantic={'status':'reviewable_candidate' if changed_count else 'unchanged_candidate','protected_pixels_equal':bool(all_preserved),'painted_classes':[CLASS_NAMES[value] for value in selected_ids],'protected_classes':options.get('protected_classes',[]),'blocked_cross_class_texels':blocked,'changed_pixels':changed_count,'occupied_texels':total,'observed_texels':observed_count,'generated_texels':generated_count,'propagated_texels':filled_count,'metrics':metrics,'channel_roundtrip':channels,'confidence':None,'scope':'Observed registered pixels and categorical masks; generated/propagated appearance is an estimate, not ground truth.'}
    report={'provider':'semantic_reference','geometry':geometry,'materials':records,'uv':[record['uv'] for record in records],'semantic':semantic,'neural':neural,'copied_percent':round(observed_count/max(total,1)*100,2),'synthesized_percent':round(generated_count/max(total,1)*100,2),'unresolved_percent':round((total-observed_count-generated_count-filled_count)/max(total,1)*100,2),'coverage_scope':'Reference-supported occupied UV texels; BlendWeight distinguishes copied from prior mixtures.','resolution':'preserved source atlas','views':list(analysis['views']),'seconds':round(time.perf_counter()-started,3),'illumination_disentangled':False,'provenance_values':{'0':'prior albedo retained','1':'observed reference with neural categorical mask','2':'observed reference with manual mask','3':'same-class surface propagation','4':'generated multiview estimate','5':'observed/prior mixture','6':'manual observed/prior mixture','7':'propagation/prior mixture','8':'generated/prior mixture'},'limitations':['Portrait-only automatic parsing; whole-body fine categories require manual evidence.','Unknown/unobserved areas retain previous albedo unless explicit bounded completion.','Texture does not repair missing hair volume or body anatomy; use the separate hair/modeling module.','No physical lighting disentanglement, detailed neural PBR or universal fidelity guarantee.']}
    (directory/'texture.json').write_text(json.dumps(report,indent=2),encoding='utf-8');return report
