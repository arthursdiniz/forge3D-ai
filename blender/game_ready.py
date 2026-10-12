"""Actual CPU high-to-low color/normal baking, preserving the source asset."""
import json,math,time
from pathlib import Path
import bpy

def build_game_ready(directory,options):
    import numpy as np
    from blender.pipeline import meshes,select_all_meshes,stats
    directory=Path(directory).resolve();textures=directory/'textures';textures.mkdir(parents=True,exist_ok=True)
    started=time.perf_counter();target=int(options['target_triangles']);resolution=int(options.get('texture_resolution',1024))
    if target<100 or resolution not in [1024,2048,4096]:raise ValueError('Invalid Game Ready budget/bake resolution.')
    before=stats();source_triangles=before['triangles']
    # Joining in the working scene keeps distinct shells and original UV islands.
    # Input files are never modified, welded, remeshed or filled.
    select_all_meshes();bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
    for obj in meshes():
        if obj.data.uv_layers:obj.data.uv_layers.active.name='UVMap'
    if len(meshes())>1:bpy.ops.object.join()
    high=bpy.context.view_layer.objects.active;high.name='HighPoly_Source'
    low=high.copy();low.data=high.data.copy();bpy.context.collection.objects.link(low);low.name='GameReady_Model'
    # glTF duplicates vertices at UV seams. Decimating those disconnected patches
    # opens holes. Reconnect only exact, uniquely matched smooth seam edges on LOW;
    # high geometry/materials/UVs remain untouched for the transfer.
    from backend.topology_seams import reconnect_uv_seams,small_component_faces
    low.data.calc_loop_triangles()
    vertices=np.array([v.co[:] for v in low.data.vertices]);faces=np.array([t.vertices[:] for t in low.data.loop_triangles])
    normal_sum=np.zeros_like(vertices)
    for loop in low.data.loops:normal_sum[loop.vertex_index]+=np.asarray(low.data.corner_normals[loop.index].vector)
    normals=normal_sum/np.maximum(np.linalg.norm(normal_sum,axis=1,keepdims=True),1e-20)
    materials=np.array([low.data.polygons[t.polygon_index].material_index for t in low.data.loop_triangles])
    joined,joined_faces,joined_normals,seam_report=reconnect_uv_seams(vertices,faces,normals,materials)
    keep_small=small_component_faces(joined_faces)
    small_faces=joined_faces[keep_small] if source_triangles>target else np.empty((0,3),int)
    main_faces=joined_faces[~keep_small] if source_triangles>target else joined_faces
    if source_triangles>target and (not len(main_faces) or target-len(small_faces)<100):raise ValueError('Orçamento insuficiente para preservar componentes pequenos; use mais triângulos.')
    def replace_data(points,triangles,normal_values):
        used,inverse=np.unique(triangles.reshape(-1),return_inverse=True)
        data=bpy.data.meshes.new('LowPoly_ConnectedUVSeams');data.from_pydata(points[used].tolist(),[],inverse.reshape(-1,3).tolist());data.update()
        data.normals_split_custom_set_from_vertices(normal_values[used].tolist())
        for polygon in data.polygons:polygon.use_smooth=True
        low.data=data
    replace_data(joined,main_faces,joined_normals)
    bpy.ops.object.select_all(action='DESELECT');low.select_set(True);bpy.context.view_layer.objects.active=low
    if source_triangles>target:
        modifier=low.modifiers.new('ExplicitTriangleBudget','DECIMATE');modifier.ratio=(target-len(small_faces))/len(main_faces);modifier.use_collapse_triangulate=True
        bpy.ops.object.modifier_apply(modifier=modifier.name)
    triangulate=low.modifiers.new('ExportTriangles','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=triangulate.name)
    if len(small_faces):
        low.data.calc_loop_triangles()
        reduced_points=np.array([v.co[:] for v in low.data.vertices]);reduced_faces=np.array([t.vertices[:] for t in low.data.loop_triangles]);reduced_normals=np.array([v.normal[:] for v in low.data.vertices])
        used,inverse=np.unique(small_faces.reshape(-1),return_inverse=True)
        replace_data(np.vstack([reduced_points,joined[used]]),np.vstack([reduced_faces,inverse.reshape(-1,3)+len(reduced_points)]),np.vstack([reduced_normals,joined_normals[used]]))
    seam_report.update(small_component_faces_preserved=int(len(small_faces)),small_component_policy='Components <=100 faces remain exact; budget is spent on larger components. No automatic fragment removal.')
    # A fresh atlas serves the actual transfer; high-resolution material/UVs remain intact on high.
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=math.radians(66),island_margin=.018);bpy.ops.object.mode_set(mode='OBJECT')
    material=bpy.data.materials.new('Forge3D_GameReady');material.use_nodes=True;low.data.materials.clear();low.data.materials.append(material)
    for polygon in low.data.polygons:polygon.material_index=0
    tree=material.node_tree;shader=tree.nodes.get('Principled BSDF');shader.inputs['Base Color'].default_value=(.5,.5,.5,1);shader.inputs['Roughness'].default_value=.65;shader.inputs['Metallic'].default_value=0
    scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=1
    scene.render.bake.use_selected_to_active=True;scene.render.bake.use_cage=False;scene.render.bake.margin=max(8,resolution//128)
    height=max(before['dimensions'][2],max(before['dimensions'])*.01)
    scene.render.bake.cage_extrusion=height*.015;scene.render.bake.max_ray_distance=height*.03
    scene.render.bake.use_clear=True
    def bake(name,kind,noncolor=False):
        image=bpy.data.images.new(name,width=resolution,height=resolution,alpha=False)
        image.colorspace_settings.name='Non-Color' if noncolor else 'sRGB'
        node=tree.nodes.new('ShaderNodeTexImage');node.image=image
        for other in tree.nodes:other.select=False
        node.select=True;tree.nodes.active=node
        bpy.ops.object.select_all(action='DESELECT');high.select_set(True);low.select_set(True);bpy.context.view_layer.objects.active=low
        if kind=='DIFFUSE':
            scene.render.bake.use_pass_direct=False;scene.render.bake.use_pass_indirect=False;scene.render.bake.use_pass_color=True
        if kind=='NORMAL':scene.render.bake.normal_space='TANGENT';scene.render.bake.normal_r='POS_X';scene.render.bake.normal_g='POS_Y';scene.render.bake.normal_b='POS_Z'
        bake_started=time.perf_counter();bpy.ops.object.bake(type=kind)
        pixels=np.asarray(image.pixels[:],dtype=np.float32).reshape(resolution,resolution,4)
        if not np.isfinite(pixels).all():raise RuntimeError('Bake produced non-finite pixels.')
        image.filepath_raw=str(textures/(name+'.png'));image.file_format='PNG';image.save()
        return image,node,{'performed':True,'type':kind,'resolution':resolution,'seconds':round(time.perf_counter()-bake_started,2),'pixel_channel_std':np.std(pixels[:,:,:3],axis=(0,1)).tolist(),'source':'actual selected high geometry/material to active low UVs, Cycles CPU'}
    base,base_node,color_report=bake('BaseColor_'+str(resolution),'DIFFUSE')
    tree.links.new(base_node.outputs['Color'],shader.inputs['Base Color'])
    normal_report={'performed':False}
    if options.get('bake_normal'):
        normal,node,normal_report=bake('Normal_'+str(resolution),'NORMAL',True)
        normal_report['normal_variation']=max(normal_report['pixel_channel_std'])
        normal_report['space']='tangent/OpenGL +Y'
        normal_map=tree.nodes.new('ShaderNodeNormalMap');normal_map.space='TANGENT';normal_map.uv_map=low.data.uv_layers.active.name
        tree.links.new(node.outputs['Color'],normal_map.inputs['Color']);tree.links.new(normal_map.outputs['Normal'],shader.inputs['Normal'])
    high.select_set(False);bpy.data.objects.remove(high,do_unlink=True);low.select_set(True);bpy.context.view_layer.objects.active=low
    after=stats()
    report={'source_triangles':source_triangles,'requested_triangles':target,'actual_triangles':after['triangles'],'budget_method':'Blender collapse decimation; approximate triangle budget, not quad retopology','uv_seam_topology':seam_report,'texture_resolution':resolution,'color_bake':color_report,'normal_bake':normal_report,'uv_method':'new Smart UV atlas for actual high-to-low transfer','source_preserved':True,'automatic_hole_filling':False,'rig_ready':False,'seconds':round(time.perf_counter()-started,2),'roughness':{'method':'neutral constant','value':.65},'metallic':{'method':'neutral constant','value':0},'warnings':['Decimation can lose silhouette/detail; compare views before Unity use.','Normal bake preserves surface shading detail, not lost anatomy or silhouette.','Higher texture dimensions do not recreate details absent from the source.']}
    (directory/'game_ready.json').write_text(json.dumps(report,indent=2),encoding='utf-8');return report
