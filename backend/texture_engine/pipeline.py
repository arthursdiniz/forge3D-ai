"""Visible observations only; source geometry is never reconstructed or moved."""
import json
import time
from pathlib import Path
import numpy as np

def texture_scene(scene,references,directory,options,calibrated=None):
    import trimesh
    from PIL import Image
    from .uv import prepare_uv
    from .identity import compare_geometry,world_triangles
    from .materials import build_material,unity_metallic_smoothness
    from ..neural_texture import rasterize_positions,pad_texture
    from ..reference_texture import project_reference_colors,NEUTRAL
    from ..character_quality import canonical_vertices,view_vertices
    from .texture_fusion import fuse_observations,gradient_reference
    started=time.perf_counter();directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    if (directory/'model.glb').exists():raise ValueError('Output model already exists; create a new version.')
    resolution=options['resolution'];padding=max(4,resolution//256)
    result,uv_reports=prepare_uv(scene,options.get('uv_mode','auto'),resolution)
    source_names={getattr(mesh.visual.material,'name',None) or f'Material_{index:03d}' for index,mesh in enumerate(result.geometry.values())}
    if set(options.get('materials',{}))-source_names:raise ValueError('Material overrides reference an unknown source material.')
    triangles=world_triangles(scene);world=triangles.reshape(-1,3);faces=np.arange(len(world)).reshape(-1,3)
    canonical=canonical_vertices(world,options.get('front_axis','negative_y'))
    records=[];total=covered=0;used_names=set()
    for index,node in enumerate(result.graph.nodes_geometry):
        matrix,name=result.graph[node];mesh=result.geometry[name];previous=mesh.visual.material
        material_name=getattr(previous,'name',None) or f'Material_{index:03d}'
        source_material_name=material_name
        if material_name in used_names:material_name+=f'__texture_{index:03d}'
        used_names.add(material_name)
        positions=trimesh.transform_points(mesh.vertices,matrix)
        normal_matrix=np.linalg.inv(matrix[:3,:3]).T
        normals=np.asarray(mesh.vertex_normals)@normal_matrix.T
        normals/=np.maximum(np.linalg.norm(normals,axis=1,keepdims=True),1e-12)
        positions=rasterize_positions(positions,mesh.faces,mesh.visual.uv,resolution)
        normal_raster=rasterize_positions(normals,mesh.faces,mesh.visual.uv,resolution)
        occupied=positions[...,3]>.5;points=canonical_vertices(positions[occupied,:3],options.get('front_axis','negative_y'));vectors=canonical_vertices(normal_raster[occupied,:3],options.get('front_axis','negative_y'))
        rgb=np.full((len(points),3),NEUTRAL,np.float32);confidence=np.zeros(len(points),np.float32);selected=np.zeros(len(points),np.uint8)
        observations=[];weights=[];gradients=[]
        for view_index,(view,rgba) in enumerate(references.items(),1):
            rgba=np.asarray(rgba)
            if calibrated is None:
                if rgba[...,3].min()==255:raise ValueError('Projection requires a real foreground alpha mask.')
                colors,weight=project_reference_colors(view_vertices(canonical,view),faces,view_vertices(points,view),view_vertices(vectors,view),rgba)
                edge,_=project_reference_colors(view_vertices(canonical,view),faces,view_vertices(points,view),view_vertices(vectors,view),gradient_reference(rgba))
            else:
                colors,weight=calibrated.project(view,points,vectors,rgba)
                edge,_=calibrated.project(view,points,vectors,gradient_reference(rgba))
            observations.append(colors);weights.append(weight);gradients.append(edge[:,0])
        fused=fuse_observations(np.stack(observations,axis=1),np.stack(weights,axis=1),np.stack(gradients,axis=1),options.get('fusion','robust'))
        rgb=fused['rgb'];confidence=fused['confidence'];selected=fused['source_view']
        observed=confidence>0;count=int(occupied.sum());total+=count;covered+=int(observed.sum())
        canvas=np.full((resolution,resolution,3),NEUTRAL,np.float32);canvas[occupied]=rgb;canvas=pad_texture(canvas,occupied,padding)
        image=Image.fromarray(np.rint(np.clip(canvas,0,1)*255).astype('u1')).transpose(Image.Transpose.FLIP_TOP_BOTTOM).convert('RGBA')
        # Preserve source alpha independently of new RGB when UVs are preserved.
        original_image=getattr(previous,'baseColorTexture',None)
        if original_image is not None and getattr(previous,'alphaMode',None) in ['MASK','BLEND'] and not uv_reports[index]['created']:
            alpha=original_image.convert('RGBA').getchannel('A').resize((resolution,resolution),Image.Resampling.BILINEAR);image.putalpha(alpha)
        folder=directory/'textures'/f'{index:03d}';folder.mkdir(parents=True,exist_ok=True)
        image.save(folder/'Albedo.png')
        for key,label in [('source_view','SourceView'),('contributors','Contributors'),('mixed','Mixed'),('conflict','Conflict')]:
            values=np.zeros((resolution,resolution),np.uint8);values[occupied]=fused[key].astype('u1')*(255 if key in ['mixed','conflict'] else 1)
            Image.fromarray(values).transpose(Image.Transpose.FLIP_TOP_BOTTOM).save(folder/(label+'.png'))
        mask=np.zeros((resolution,resolution),np.uint8);mask[occupied]=np.rint(confidence*255).astype('u1')
        Image.fromarray(mask).transpose(Image.Transpose.FLIP_TOP_BOTTOM).save(folder/'Confidence.png')
        provenance=np.zeros((resolution,resolution),np.uint8);provenance[occupied]=np.where(observed,2 if calibrated else 1,3)
        Image.fromarray(provenance).transpose(Image.Transpose.FLIP_TOP_BOTTOM).save(folder/'Provenance.png')
        palette=np.array([[24,30,34],[48,190,150],[75,140,235],[205,205,205]],dtype='u1')
        Image.fromarray(palette[provenance]).transpose(Image.Transpose.FLIP_TOP_BOTTOM).save(folder/'ProvenancePreview.png')
        coverage=np.zeros((resolution,resolution),np.uint8);coverage[occupied]=np.uint8(observed)*255
        Image.fromarray(coverage).transpose(Image.Transpose.FLIP_TOP_BOTTOM).save(folder/'Coverage.png')
        occupancy=np.uint8(occupied)*255
        Image.fromarray(occupancy).transpose(Image.Transpose.FLIP_TOP_BOTTOM).save(folder/'UV.png')
        material=build_material(previous,image,material_name,options.get('materials',{}).get(source_material_name,{}));mesh.visual=trimesh.visual.TextureVisuals(uv=mesh.visual.uv.copy(),material=material)
        maps={'albedo':f'textures/{index:03d}/Albedo.png','confidence':f'textures/{index:03d}/Confidence.png','coverage':f'textures/{index:03d}/Coverage.png','provenance':f'textures/{index:03d}/Provenance.png','provenance_preview':f'textures/{index:03d}/ProvenancePreview.png','uv':f'textures/{index:03d}/UV.png'}
        maps.update({key:f'textures/{index:03d}/{label}.png' for key,label in [('source_view','SourceView'),('contributors','Contributors'),('mixed','Mixed'),('conflict','Conflict')]})
        for attribute,label in [('normalTexture','normal'),('occlusionTexture','occlusion'),('metallicRoughnessTexture','metallic_roughness'),('emissiveTexture','emissive')]:
            value=getattr(material,attribute,None)
            if value is not None:value.save(folder/(label+'.png'));maps[label]=f'textures/{index:03d}/{label}.png'
        if material.metallicRoughnessTexture is not None:
            packed=unity_metallic_smoothness(material.metallicRoughnessTexture,material.metallicFactor if material.metallicFactor is not None else 1.,material.roughnessFactor if material.roughnessFactor is not None else 1.)
            Image.fromarray(packed).save(folder/'UnityMetallicSmoothness.png');maps['unity_metallic_smoothness']=f'textures/{index:03d}/UnityMetallicSmoothness.png'
        records.append({'name':material_name,'geometry':name,'node':node,'maps':maps,'coverage_percent':round(float(observed.mean()*100),2),'metallic':material.metallicFactor,'roughness':material.roughnessFactor,'alpha_mode':material.alphaMode or 'OPAQUE','alpha_cutoff':material.alphaCutoff,'double_sided':material.doubleSided,'normal_preserved':material.normalTexture is not None,'provenance':{'albedo':'neural generated views' if calibrated else 'visible reference projection','normal':'preserved source map' if material.normalTexture is not None else 'absent','metallic_roughness':'preserved source map and factors' if material.metallicRoughnessTexture is not None else 'constant factors'},'color_space':{'albedo':'sRGB','normal':'linear','metallic_roughness':'linear','occlusion':'linear'}})
    report=compare_geometry(scene,result)
    if not report['equivalent']:raise ValueError('Geometry identity failed before export.')
    result.export(directory/'model.glb',include_normals=True)
    restored=trimesh.load(directory/'model.glb',force='scene',process=False)
    exported=compare_geometry(scene,restored)
    if not exported['equivalent']:raise ValueError('Geometry identity failed after GLB reimport.')
    percent=round(covered/max(1,total)*100,2)
    report={'provider':options['provider'],'geometry':exported,'uv':uv_reports,'materials':records,'resolution':resolution,'copied_percent':0 if calibrated else percent,'synthesized_percent':percent if calibrated else 0,'unresolved_percent':round(100-percent,2),'coverage_scope':'occupied UV texels, not mesh area; angle/depth confidence is not a semantic fidelity score','provenance_values':{'0':'outside UV','1':'copied reference','2':'neural synthesis','3':'unresolved'},'padding_pixels':padding,'fusion':'highest visibility/depth/angle confidence; no averaging of conflicting views','views':list(references),'illumination_disentangled':False,'seconds':round(time.perf_counter()-started,3),'limitations':['Unobserved reference surfaces remain neutral.','Estimated projection requires matching pose and labeled views.','Generated views can contain semantic errors and baked lighting; inspect seams/face manually.']}
    report['fusion_mode']=options.get('fusion','robust')
    report['fusion']='Independent observed RGB/confidence; winner on incompatible colors/high gradients; linear-light blend only for compatible smooth observations.' if report['fusion_mode']=='robust' else 'Highest visibility/depth/angle confidence observation; observed RGB is not gray-blended.'
    report['source_view_values']={str(index):view for index,view in enumerate(references,1)}
    report['contributor_encoding']='Bitmask: bit0 corresponds to view1; zero means no observation.'
    (directory/'texture.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report
