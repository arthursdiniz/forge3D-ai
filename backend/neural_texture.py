"""Surface position rasterization and dense color-field sampling, not upscale."""
from pathlib import Path
import numpy as np

def rasterize_positions(vertices,faces,uv,resolution,face_ids=False):
    import moderngl
    context=moderngl.create_standalone_context()
    width,height=(resolution,resolution) if isinstance(resolution,int) else resolution
    try:
        program=context.program(vertex_shader='''#version 330
in vec2 in_uv; in vec3 in_pos; out vec3 position;
void main(){position=in_pos;gl_Position=vec4(in_uv*2.0-1.0,0.0,1.0);}''',fragment_shader='''#version 330
in vec3 position; out vec4 output_position;
void main(){output_position=vec4(position,1.0);}'''.replace('1.0);','float(gl_PrimitiveID+1));') if face_ids else '''#version 330
in vec3 position; out vec4 output_position;
void main(){output_position=vec4(position,1.0);}''')
        positions=context.buffer(np.asarray(vertices,dtype='f4').tobytes())
        coords=context.buffer(np.asarray(uv,dtype='f4').tobytes())
        indices=context.buffer(np.asarray(faces,dtype='i4').tobytes())
        vao=context.vertex_array(program,[(coords,'2f','in_uv'),(positions,'3f','in_pos')],indices)
        attachment=context.texture((width,height),4,dtype='f4')
        target=context.framebuffer(color_attachments=[attachment])
        target.use()
        target.clear(0,0,0,0)
        context.disable(moderngl.DEPTH_TEST|moderngl.CULL_FACE)
        vao.render(mode=moderngl.TRIANGLES)
        pixels=np.frombuffer(attachment.read(),dtype='f4').reshape(height,width,4).copy()
        vao.release();indices.release();coords.release();positions.release();target.release();attachment.release();program.release()
        return pixels
    finally:
        context.release()

def pad_texture(rgb,mask,padding):
    from scipy.ndimage import distance_transform_edt
    output=np.full(rgb.shape,0.5,dtype=np.float32)
    output[mask]=rgb[mask]
    distance,indices=distance_transform_edt(~mask,return_indices=True)
    fill=(distance<=padding)&~mask
    output[fill]=rgb[indices[0][fill],indices[1][fill]]
    return output

def bake_neural_texture(mesh,query_colors,resolution,directory):
    import time
    import trimesh
    import xatlas
    from PIL import Image
    started=time.perf_counter()
    directory=Path(directory)
    directory.mkdir(parents=True,exist_ok=True)
    atlas=xatlas.Atlas()
    atlas.add_mesh(np.asarray(mesh.vertices,dtype=np.float32),np.asarray(mesh.faces,dtype=np.uint32))
    packing=xatlas.PackOptions()
    packing.resolution=resolution
    # Measured on the same 238,760-triangle robot: 16 -> 4 pack pixels
    # increased actual 2048 surface texels from 459,010 to 1,652,530.
    packing.padding=4
    packing.bilinear=True
    atlas.generate(pack_options=packing)
    mapping,indices,uv=atlas[0]
    vertices=mesh.vertices[mapping]
    raster=rasterize_positions(vertices,indices,uv,resolution)
    mask=raster[...,3]>0.5
    if not np.any(mask):raise RuntimeError('UV atlas sem texels válidos.')
    positions=raster[mask,:3]
    colors=np.empty((len(positions),3),dtype=np.float32)
    # Stream GPU queries and CPU results. No giant temporary GPU output.
    for offset in range(0,len(positions),32768):
        colors[offset:offset+32768]=query_colors(positions[offset:offset+32768])
    if not np.isfinite(colors).all():raise RuntimeError('Cor neural contém valores inválidos.')
    rgb=np.zeros((resolution,resolution,3),dtype=np.float32)
    rgb[mask]=colors
    rgb=pad_texture(rgb,mask,packing.padding)
    image=Image.fromarray(np.clip(np.rint(rgb*255),0,255).astype(np.uint8)).transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    image.save(directory/'Albedo.png')
    material=trimesh.visual.material.PBRMaterial(name='Forge3D_NeuralAlbedo',baseColorTexture=image,metallicFactor=0.0,roughnessFactor=0.65,alphaMode='OPAQUE')
    visual=trimesh.visual.TextureVisuals(uv=uv,material=material)
    textured=trimesh.Trimesh(vertices=vertices,faces=indices,vertex_normals=mesh.vertex_normals[mapping],visual=visual,process=False)
    textured.export(directory.parent/'textured_generation.glb',include_normals=True)
    return {'method':'neural_atlas','uv_unwrap':'xatlas','texture_resolution':resolution,'atlas_size':[atlas.width,atlas.height],'atlas_charts':atlas.chart_count,'atlas_utilization':float(atlas.utilization),'neural_texel_queries':int(mask.sum()),'coverage_percent':round(float(mask.mean()*100),2),'padding_pixels':packing.padding,'seconds':round(time.perf_counter()-started,2),'vertex_color_interpolation':False,'pbr_channels':['base_color'],'illumination_disentangled':False,'color_space':'sRGB PNG; no second transfer curve'}
