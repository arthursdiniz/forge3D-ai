import numpy as np

def inspect_uv(mesh,resolution=512):
    import moderngl
    uv=getattr(mesh.visual,'uv',None)
    report={'valid':False,'overlap_percent':0.,'occupancy_percent':0.,'raster_resolution':resolution}
    if uv is None or np.shape(uv)!=(len(mesh.vertices),2) or not np.isfinite(uv).all():return report
    uv=np.asarray(uv)
    if uv.min()<-1e-6 or uv.max()>1+1e-6:return report
    corners=uv[mesh.faces];edges=corners[:,1:]-corners[:,:1]
    areas=np.abs(edges[:,0,0]*edges[:,1,1]-edges[:,0,1]*edges[:,1,0])/2
    report['degenerate_faces']=int((areas<1e-12).sum())
    if (areas<1e-12).mean()>.001:return report
    context=moderngl.create_standalone_context()
    try:
        program=context.program(vertex_shader='#version 330\nin vec2 uv;void main(){gl_Position=vec4(uv*2-1,0,1);}',fragment_shader='#version 330\nout float count;void main(){count=1.;}')
        coords=context.buffer(uv.astype('f4').tobytes());indices=context.buffer(np.asarray(mesh.faces,dtype='i4').tobytes())
        vao=context.vertex_array(program,[(coords,'2f','uv')],indices)
        texture=context.texture((resolution,resolution),1,dtype='f4');target=context.framebuffer([texture]);target.use();target.clear()
        context.disable(moderngl.DEPTH_TEST|moderngl.CULL_FACE);context.enable(moderngl.BLEND);context.blend_func=(moderngl.ONE,moderngl.ONE)
        vao.render(moderngl.TRIANGLES)
        counts=np.frombuffer(texture.read(),dtype='f4');occupied=counts>.5
        report.update(valid=bool(occupied.any()),overlap_percent=round(float((counts>1.5).sum()/max(1,occupied.sum())*100),4),occupancy_percent=round(float(occupied.mean()*100),4))
        vao.release();indices.release();coords.release();target.release();texture.release();program.release()
    finally:context.release()
    return report

def prepare_uv(scene,mode,resolution):
    import trimesh
    import xatlas
    result=scene.copy();reports=[]
    edges={child:(parent,data) for parent,child,data in result.graph.to_edgelist()}
    originals=list(result.graph.nodes_geometry)
    for number,node in enumerate(originals):
        _,name=scene.graph[node];mesh=scene.geometry[name].copy()
        if isinstance(getattr(mesh.visual,'material',None),trimesh.visual.material.MultiMaterial):raise ValueError('Split multimaterial primitives on static import before texturing.')
        material=getattr(mesh.visual,'material',None)
        data_maps=any(getattr(material,key,None) is not None for key in ['normalTexture','occlusionTexture','metallicRoughnessTexture','emissiveTexture'])
        data_maps=data_maps or (getattr(material,'alphaMode',None) in ['MASK','BLEND'] and getattr(material,'baseColorTexture',None) is not None)
        report=inspect_uv(mesh)
        replace=mode=='new' or not report['valid'] or report['overlap_percent']>.5
        if replace and mode=='preserve':raise ValueError('Invalid UV or overlap: repair UVs or choose auto without existing data maps.')
        if replace and data_maps:raise ValueError('UV replacement requires tangent/data-map rebake; preserve valid UVs or repair in Blender.')
        if replace:
            atlas=xatlas.Atlas();atlas.add_mesh(np.asarray(mesh.vertices,dtype='f4'),np.asarray(mesh.faces,dtype='u4'))
            pack=xatlas.PackOptions();pack.resolution=resolution;pack.padding=max(4,resolution//256);pack.bilinear=True
            atlas.generate(pack_options=pack)
            mapping,faces,uv=atlas[0]
            mesh=trimesh.Trimesh(vertices=mesh.vertices[mapping],faces=faces,vertex_normals=mesh.vertex_normals[mapping],visual=trimesh.visual.TextureVisuals(uv=uv,material=material),process=False)
            report=inspect_uv(mesh)
            if not report['valid'] or report['overlap_percent']>.5:raise ValueError('xatlas returned invalid or overlapping UVs.')
        unique=f'texture_{number:03d}';result.geometry[unique]=mesh
        parent,data=edges[node];result.graph.update(frame_from=parent,frame_to=node,matrix=data['matrix'],geometry=unique,metadata=data.get('metadata',{}))
        reports.append({**report,'node':node,'geometry':unique,'created':replace,'padding_pixels':max(4,resolution//256)})
    used={result.graph[node][1] for node in result.graph.nodes_geometry}
    for name in list(result.geometry):
        if name not in used:del result.geometry[name]
    return result,reports
