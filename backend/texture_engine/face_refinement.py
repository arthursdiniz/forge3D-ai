"""Immutable regional painting, exact protected pixels and measured candidates."""
import copy
import json
import time
from pathlib import Path
import numpy as np

def refine_scene(scene,rgba,options,directory,source_folder=None):
    import trimesh
    from PIL import Image
    from scipy.ndimage import distance_transform_edt,map_coordinates
    from ..neural_texture import rasterize_positions
    from ..character_quality import canonical_vertices
    from .region_camera import RegionCamera
    from .face_projection import project_region
    from .region_masks import editable_mask,source_coordinates,polygon_mask,rectangle
    from .face_reference import crop_reference
    from .texture_metrics import image_metrics,candidate_improved
    from .identity import compare_geometry
    from .uv import inspect_uv
    from .texture_seams import inspect_seams,correct_seams,uv_density
    from .cached_views import CachedViews
    from .texture_fusion import srgb_to_linear,linear_to_srgb
    started=time.perf_counter();directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    if (directory/'model.glb').exists():raise ValueError('Output model exists; create a new regional version.')
    if not options.get('reviewed_alignment'):raise ValueError('Review reference/model alignment before applying a correction.')
    names=[scene.graph[node][1] for node in scene.graph.nodes_geometry]
    if len(set(names))!=len(names):raise ValueError('Shared instances require separate texture materials for localized editing; original preserved.')
    original_reference=Image.fromarray(rgba).convert('RGBA');reference=crop_reference(original_reference,options['source_box'],margin=1.0);reference['source_crop'].save(directory/'face_reference.png');reference['enlarged'].save(directory/'face_reference_enlarged.png');crop_reference(original_reference,options['source_box'],margin=0)['source_crop'].save(directory/'face_reference_core.png')
    camera=RegionCamera(scene,options.get('front_axis','negative_y'),options.get('camera_resolution',1024))
    cache=CachedViews(scene,options.get('front_axis','negative_y'),source_folder if options.get('cached_views',True) else None)
    Image.fromarray(camera.image).save(directory/'region_before_full.png')
    result=scene.copy();records=[];uv_reports=[];outside_unchanged=True;changed_total=occupied_total=cache_total=0;counts={1:0,2:0,3:0,4:0,5:0,6:0};previous_counts=dict(counts)
    prior={}
    if source_folder and (Path(source_folder)/'texture.json').is_file():prior=json.loads((Path(source_folder)/'texture.json').read_text())
    for index,node in enumerate(scene.graph.nodes_geometry):
        matrix,name=scene.graph[node];mesh=scene.geometry[name];previous=getattr(mesh.visual,'material',None);source_image=getattr(previous,'baseColorTexture',None)
        result.geometry[name].vertex_normals=np.asarray(mesh.vertex_normals).copy()
        if source_image is None:raise ValueError('Regional refinement needs an existing albedo texture; texturize globally first.')
        if not isinstance(previous,trimesh.visual.material.PBRMaterial):raise ValueError('Prepare a core PBR source before regional editing.')
        uv=inspect_uv(mesh)
        if not uv['valid'] or uv['overlap_percent']>.5:raise ValueError('Invalid UV/overlap: localized painting requires valid preserved UVs.')
        uv_reports.append({**uv,'created':False,'node':node,'geometry':name,'padding_pixels':0})
        original=np.asarray(source_image.convert('RGBA')).copy();height,width=original.shape[:2]
        if max(width,height)>4096:raise ValueError('Regional atlas exceeds4096px; source preserved.')
        world=trimesh.transform_points(mesh.vertices,matrix);world_normals=np.asarray(mesh.vertex_normals)@np.linalg.inv(matrix[:3,:3])
        world=canonical_vertices(world,options.get('front_axis','negative_y'));world_normals=canonical_vertices(world_normals,options.get('front_axis','negative_y'))
        positions=rasterize_positions(world,mesh.faces,mesh.visual.uv,(width,height),face_ids=True);normals=rasterize_positions(world_normals,mesh.faces,mesh.visual.uv,(width,height));occupied=positions[...,3]>.5
        colors,confidence,xy,_=project_region(camera,positions[occupied,:3],normals[occupied,:3],rgba,options,index+1,positions[occupied,3])
        cached=np.zeros(len(colors),bool)
        if cache.valid:
            eligible=editable_mask(xy,options)&(confidence<=0)&(camera.visibility(positions[occupied,:3],normals[occupied,:3],index+1,positions[occupied,3])>0)
            if eligible.any():
                rgb,weight=cache.project(positions[occupied,:3][eligible],normals[occupied,:3][eligible]);indices=np.flatnonzero(eligible);indices=indices[weight>0]
                colors[indices]=rgb[weight>0];confidence[indices]=weight[weight>0];cached[indices]=True
        material_name=previous.name or f'Material_{index:03d}'
        if options.get('materials') and material_name not in options['materials']:confidence[:]=0
        edit=np.zeros((height,width),bool);edit[occupied]=confidence>0
        amount=np.zeros((height,width),np.float32);amount[edit]=options.get('intensity',1)
        feather=options.get('feather_pixels',4)
        if feather:amount*=np.clip(distance_transform_edt(edit)/feather,0,1)
        before=original[::-1].copy();paint=before.copy();factor=np.asarray(previous.baseColorFactor if previous.baseColorFactor is not None else [255]*4,dtype=float)/255
        if np.any(factor[:3]<.01) and edit.any():raise ValueError('Source albedo factor suppresses editable color; adjust material explicitly before refinement.')
        texels=linear_to_srgb(np.clip(srgb_to_linear(colors)/np.maximum(factor[:3],.01),0,1))*255
        requested=np.zeros((height,width,3),np.float32);requested[occupied]=texels
        blended=srgb_to_linear(before[edit,:3]/255)*(1-amount[edit,None])+srgb_to_linear(requested[edit]/255)*amount[edit,None]
        paint[edit,:3]=np.rint(linear_to_srgb(blended)*255).clip(0,255).astype('u1')
        output=paint[::-1].copy();mask=edit[::-1].copy();seams_before=inspect_seams(mesh,output)
        if options.get('seam_correction',True):output=correct_seams(mesh,output,mask)
        changed=np.any(output[...,:3]!=original[...,:3],axis=2)
        preserved=bool(np.array_equal(output[~mask],original[~mask]) and np.array_equal(output[...,3],original[...,3]));outside_unchanged&=preserved
        material=copy.deepcopy(previous);material.baseColorTexture=Image.fromarray(output);result.geometry[name].visual.material=material
        folder=directory/'textures'/f'{index:03d}';folder.mkdir(parents=True,exist_ok=True);Image.fromarray(output).save(folder/'Albedo.png');source_image.save(folder/'PreviousAlbedo.png');Image.fromarray(mask.astype('u1')*255).save(folder/'EditMask.png')
        Image.fromarray(np.rint(amount[::-1]*255).astype('u1')).save(folder/'BlendWeight.png')
        conf=np.zeros((height,width),np.uint8);conf[occupied]=np.rint(confidence*255).astype('u1');Image.fromarray(conf[::-1]).save(folder/'Confidence.png')
        provenance=np.zeros((height,width),np.uint8);provenance[occupied]=4;previous_confidence=np.zeros((height,width),np.uint8)
        for old_record in prior.get('materials',[]):
            if old_record['name']==material_name and source_folder and old_record.get('maps',{}).get('provenance'):
                path=(Path(source_folder)/old_record['maps']['provenance']).resolve()
                if path.is_relative_to(Path(source_folder).resolve()) and path.is_file():
                    old=np.asarray(Image.open(path))
                    if old.shape==provenance.shape:provenance=old[::-1].copy()
                confidence_path=(Path(source_folder)/old_record['maps'].get('confidence','')).resolve()
                if confidence_path.is_relative_to(Path(source_folder).resolve()) and confidence_path.is_file():
                    old_confidence=np.asarray(Image.open(confidence_path))
                    if old_confidence.shape==previous_confidence.shape:previous_confidence=old_confidence.copy()
        Image.fromarray(provenance[::-1]).save(folder/'PreviousProvenance.png');Image.fromarray(previous_confidence).save(folder/'PreviousConfidence.png')
        for value in previous_counts:previous_counts[value]+=int(((provenance==value)&occupied).sum())
        cache_mask=np.zeros((height,width),bool);cache_mask[occupied]=cached;cache_mask&=edit;cache_total+=int(cache_mask.sum())
        provenance[edit& (amount>.999)]=1;provenance[edit& (amount<=.999)]=5
        provenance[cache_mask&(amount>.999)]=2;provenance[cache_mask&(amount<=.999)]=6
        Image.fromarray(provenance[::-1]).save(folder/'Provenance.png')
        for value in counts:counts[value]+=int(((provenance==value)&occupied).sum())
        changed_total+=int(changed.sum());occupied_total+=int(occupied.sum())
        maps={key:f'textures/{index:03d}/{filename}.png' for key,filename in [('albedo','Albedo'),('previous_albedo','PreviousAlbedo'),('edit_mask','EditMask'),('blend_weight','BlendWeight'),('confidence','Confidence'),('provenance','Provenance')]}
        for attribute,label in [('normalTexture','normal'),('occlusionTexture','occlusion'),('metallicRoughnessTexture','metallic_roughness'),('emissiveTexture','emissive')]:
            value=getattr(material,attribute,None)
            if value is not None:value.save(folder/(label+'.png'));maps[label]=f'textures/{index:03d}/{label}.png'
        records.append({'name':material_name,'geometry':name,'node':node,'maps':maps,'normal_preserved':material.normalTexture is not None,'outside_unchanged':preserved,'changed_pixels':int(changed.sum()),'editable_pixels':int(mask.sum()),'atlas_size':[width,height],'uv_density':uv_density(mesh,mask,world),'seams':{'before':seams_before,'after':inspect_seams(mesh,output)},'face_density_scope':'Editable UV samples; no adaptive unwrap/rebake.'})
    after_camera=RegionCamera(result,options.get('front_axis','negative_y'),camera.size,camera.frame)
    rows,cols=np.indices((camera.size,camera.size));xy=np.column_stack([(cols.ravel()+.5)/camera.size,(rows.ravel()+.5)/camera.size]);source_xy=source_coordinates(xy,options)
    height,width=rgba.shape[:2];target=np.column_stack([map_coordinates(rgba[...,i].astype(float),[source_xy[:,1]*height-.5,source_xy[:,0]*width-.5],order=1,mode='nearest') for i in range(4)]).reshape(camera.size,camera.size,4)
    metric_mask=editable_mask(xy,options)&polygon_mask(source_xy,options.get('source_polygon') or rectangle(options['source_box']))&(source_xy.min(axis=1)>=0)&(source_xy.max(axis=1)<1)
    metric_mask=metric_mask.reshape(camera.size,camera.size)&(camera.image[...,3]>=240)&(target[...,3]>=240)
    before_metrics=image_metrics(camera.image,target,metric_mask);after_metrics=image_metrics(after_camera.image,target,metric_mask)
    improved=candidate_improved(before_metrics,after_metrics,changed_total,outside_unchanged,reference['face_min_pixels'])
    result.export(directory/'candidate.glb',include_normals=True)
    published=result if improved else scene;published.export(directory/'model.glb',include_normals=True)
    identity=compare_geometry(scene,trimesh.load(directory/'model.glb',force='scene',process=False))
    if not identity['equivalent'] or not outside_unchanged:raise ValueError('Geometry identity or protected appearance failed.')
    Image.fromarray(after_camera.image).save(directory/'region_after_full.png');Image.fromarray(np.uint8(metric_mask)*255).save(directory/'comparison_mask.png');Image.fromarray(np.rint(target).clip(0,255).astype('u1')).save(directory/'reference_aligned.png')
    for label,current in [('before',camera),('after',after_camera)]:
        for view,angle in [('front',0),('three_quarter',35),('side',90)]:Image.fromarray(current.zoom(options['target_box'],options.get('face_resolution',768),angle)).save(directory/f'face_{label}_{view}.png')
    status='improved_candidate' if improved else 'inconclusive_previous_retained'
    if not improved:
        for record in records:
            record['maps']['candidate_albedo']=record['maps']['albedo'];record['maps']['albedo']=record['maps']['previous_albedo']
            for label in ['provenance','confidence']:
                record['maps']['candidate_'+label]=record['maps'][label];record['maps'][label]=f'textures/{records.index(record):03d}/Previous{label.title()}.png'
            record['published_changed_pixels']=0
        counts=previous_counts
    report={'provider':'reference_region','geometry':identity,'materials':records,'uv':uv_reports,'resolution':max(max(r['atlas_size']) for r in records),'copied_percent':round(counts[1]/max(1,occupied_total)*100,2),'synthesized_percent':round(counts[2]/max(1,occupied_total)*100,2),'unresolved_percent':round(counts[3]/max(1,occupied_total)*100,2),'provenance_values':{'0':'outside UV','1':'copied reference','2':'prior neural synthesis','3':'prior unresolved','4':'preserved existing unknown origin','5':'reference/prior boundary mixture'},'seconds':round(time.perf_counter()-started,3),'regional':{'status':status,'published':'candidate' if improved else 'previous','requires_human_review':True,'outside_unchanged':outside_unchanged,'changed_pixels':changed_total,'metrics':{'before':before_metrics,'after':after_metrics},'reference':{key:value for key,value in reference.items() if key not in ['source_crop','enlarged']},'options':options,'inpainting':False,'geometry_refinement':False},'limitations':reference['warnings']+['Projected color/SSIM improvement is not universal facial identity.','Large-angle/hidden surfaces retain the previous texture; no skull-wide projection.','Existing UV density and facial geometry limit achievable detail.']}
    report['regional']['cache']={'available':cache.valid,'reason':cache.reason,'reprojected_texels':cache_total,'synthesized_not_copied':True,'new_inference':False}
    report['provenance_values']['6']='cached neural/prior boundary mixture'
    (directory/'texture.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report
