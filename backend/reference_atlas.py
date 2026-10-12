"""Conservative visible-reference atlas; no invented texture on unseen surfaces."""
from pathlib import Path
import time
import numpy as np

def bake_reference_atlas(scene,rgba,resolution,output):
    return bake_reference_views(scene,{'front':rgba},resolution,output,require_mask=False)

def bake_reference_views(scene,references,resolution,output,front_axis='negative_y',require_mask=True):
    import trimesh
    from PIL import Image
    from .neural_texture import rasterize_positions,pad_texture
    from .reference_texture import project_reference_colors,NEUTRAL
    from .character_quality import view_vertices,canonical_vertices
    if resolution not in [64,512,1024,2048,4096]:raise ValueError('Unsupported reference atlas resolution.')
    if not references or any(name not in ['front','back','left','right'] for name in references):raise ValueError('Use named real views, not collages.')
    output=Path(output)
    if output.exists():raise ValueError('Reference texturing requires a new output version.')
    nodes=list(scene.graph.nodes_geometry)
    if len(nodes)!=1 or len(scene.geometry)!=1:raise ValueError('Reference texturing requires one validated mesh instance.')
    start=time.perf_counter();result=scene.copy()
    matrix,name=result.graph[nodes[0]];mesh=result.geometry[name]
    if not isinstance(mesh.visual,trimesh.visual.TextureVisuals) or mesh.visual.uv is None:raise ValueError('UVs are required.')
    if not np.isfinite(mesh.visual.uv).all():raise ValueError('Nonfinite UVs.')
    vertices=trimesh.transform_points(mesh.vertices,matrix)
    normal_matrix=np.linalg.inv(matrix[:3,:3]).T
    normals=np.asarray(mesh.vertex_normals)@normal_matrix.T
    normals/=np.maximum(np.linalg.norm(normals,axis=1,keepdims=True),1e-12)
    position_raster=rasterize_positions(vertices,mesh.faces,mesh.visual.uv,resolution)
    normal_raster=rasterize_positions(normals,mesh.faces,mesh.visual.uv,resolution)
    occupied=position_raster[...,3]>.5
    if not occupied.any():raise ValueError('Empty UV atlas.')
    points=position_raster[occupied,:3];vectors=normal_raster[occupied,:3]
    vertices=canonical_vertices(vertices,front_axis);points=canonical_vertices(points,front_axis);vectors=canonical_vertices(vectors,front_axis)
    colors=np.full((len(points),3),NEUTRAL,np.float32);confidence=np.zeros(len(points),np.float32);view_coverage={}
    for view,reference in references.items():
        rgba=np.asarray(reference)
        if rgba.ndim!=3 or rgba.shape[2]!=4 or (require_mask and rgba[...,3].min()==255):raise ValueError('Reference projection requires a real alpha foreground mask per view.')
        projected,weight=project_reference_colors(view_vertices(vertices,view),mesh.faces,view_vertices(points,view),view_vertices(vectors,view),rgba,depth_resolution=1024)
        best=weight>confidence;colors[best]=projected[best];confidence[best]=weight[best]
        view_coverage[view]=round(float((weight>.5).mean()*100),2)
    rgb=np.full((resolution,resolution,3),NEUTRAL,np.float32);rgb[occupied]=colors
    rgb=pad_texture(rgb,occupied,4)
    image=Image.fromarray(np.rint(np.clip(rgb,0,1)*255).astype(np.uint8)).transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    textures=output.parent/'textures';textures.mkdir(parents=True,exist_ok=True)
    image.save(textures/'ReferenceAlbedo.png')
    uv=mesh.visual.uv.copy()
    previous=mesh.visual.material
    material=trimesh.visual.material.PBRMaterial(name='Forge3D_VisibleReference',baseColorTexture=image,normalTexture=getattr(previous,'normalTexture',None),occlusionTexture=getattr(previous,'occlusionTexture',None),metallicRoughnessTexture=getattr(previous,'metallicRoughnessTexture',None),metallicFactor=getattr(previous,'metallicFactor',None) or 0.0,roughnessFactor=getattr(previous,'roughnessFactor',None) if getattr(previous,'roughnessFactor',None) is not None else .65,alphaMode='OPAQUE')
    mesh.visual=trimesh.visual.TextureVisuals(uv=uv,material=material)
    result.export(output,include_normals=True)
    return {'method':'reference_visible_front' if list(references)==['front'] else 'reference_visible_named_views','generated':False,'hidden_surface':'neutral','texture_resolution':resolution,'visible_surface_texel_percent':round(float((confidence>.5).mean()*100),2),'view_coverage_percent':view_coverage,'views':list(references),'conditioned_geometry':False,'pbr_channels':['base_color']+(['normal'] if material.normalTexture is not None else []),'normal_map_preserved':material.normalTexture is not None,'geometry_changed':False,'illumination_disentangled':False,'seconds':round(time.perf_counter()-start,2),'limitations':'Estimated orthographic projection of labeled matching-pose views. Unobserved/occluded areas remain neutral; inspect alignment and side seams.'}
