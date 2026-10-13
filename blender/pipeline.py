"""Reviewed headless Blender pipeline: no input scripts or arbitrary operators."""
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
import bpy
import bmesh
from mathutils import Vector, Matrix
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

def meshes():
    return [obj for obj in bpy.context.scene.objects if obj.type=='MESH']

def select_all_meshes():
    bpy.ops.object.select_all(action='DESELECT')
    for obj in meshes():
        obj.select_set(True)
    if meshes():
        bpy.context.view_layer.objects.active=meshes()[0]

def stats():
    verts=triangles=uvs=0
    points=[]
    materials=[]
    for obj in meshes():
        obj.data.calc_loop_triangles()
        verts+=len(obj.data.vertices)
        triangles+=len(obj.data.loop_triangles)
        uvs+=int(bool(obj.data.uv_layers))
        # Rotated local bounding-box corners overestimate the actual mesh bounds.
        points.extend(obj.matrix_world@vertex.co for vertex in obj.data.vertices)
        for vertex in obj.data.vertices:
            if not all(math.isfinite(x) for x in vertex.co):
                raise ValueError('Nonfinite vertex')
        for material in obj.data.materials:
            if material:
                materials.append({'name':material.name,'images':[node.image.name for node in material.node_tree.nodes if node.type=='TEX_IMAGE' and node.image] if material.use_nodes else []})
    if not triangles:
        raise ValueError('Empty mesh')
    lower=Vector([min(p[i] for p in points) for i in range(3)])
    upper=Vector([max(p[i] for p in points) for i in range(3)])
    return {'triangles':triangles,'vertices':verts,'mesh_count':len(meshes()),'uv_meshes':uvs,'dimensions':list(upper-lower),'materials':materials,'bounds_min':list(lower),'bounds_max':list(upper),'finite_vertices':True}

def center():
    info=stats()
    midpoint=(Vector(info['bounds_min'])+Vector(info['bounds_max']))/2
    for obj in meshes():
        obj.location-=midpoint
    bpy.context.view_layer.update()

def integrity():
    import numpy as np
    from backend.mesh_quality import inspect_mesh
    reports=[]
    for obj in meshes():
        obj.data.calc_loop_triangles()
        vertices=np.array([obj.matrix_world@vertex.co for vertex in obj.data.vertices])
        faces=np.array([triangle.vertices for triangle in obj.data.loop_triangles])
        uv=np.array([loop.uv for loop in obj.data.uv_layers.active.data]) if obj.data.uv_layers else None
        normals=np.array([vertex.normal for vertex in obj.data.vertices])
        reports.append({'object':obj.name,**inspect_mesh(vertices,faces,uv,normals)})
    return reports

def bake_colors(directory,resolution):
    scene=bpy.context.scene
    scene.render.engine='CYCLES'
    scene.cycles.device='CPU'
    scene.cycles.samples=1
    scene.render.bake.use_clear=True
    scene.render.bake.margin=12
    directory.mkdir(exist_ok=True,parents=True)
    for index,obj in enumerate(meshes()):
        # Native UV/material textures take priority over a vertex-color bake.
        has_texture=any(material and material.use_nodes and any(node.type=='TEX_IMAGE' and node.image for node in material.node_tree.nodes) for material in obj.data.materials)
        if has_texture and obj.data.uv_layers:
            continue
        color=obj.data.color_attributes.active_color
        if not color:
            continue
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        bpy.context.view_layer.objects.active=obj
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.smart_project(angle_limit=math.radians(66),island_margin=0.015)
        bpy.ops.object.mode_set(mode='OBJECT')
        material=bpy.data.materials.new(f'Forge3D_Material_{index}')
        material.use_nodes=True
        obj.data.materials.clear()
        obj.data.materials.append(material)
        tree=material.node_tree
        tree.nodes.clear()
        vertex=tree.nodes.new('ShaderNodeVertexColor')
        vertex.layer_name=color.name
        emission=tree.nodes.new('ShaderNodeEmission')
        out=tree.nodes.new('ShaderNodeOutputMaterial')
        tree.links.new(vertex.outputs['Color'],emission.inputs['Color'])
        tree.links.new(emission.outputs[0],out.inputs['Surface'])
        image=bpy.data.images.new(f'Albedo_{index}',width=resolution,height=resolution,alpha=False)
        texture=tree.nodes.new('ShaderNodeTexImage')
        texture.image=image
        tree.nodes.active=texture
        bpy.ops.object.bake(type='EMIT')
        image.filepath_raw=str(directory/f'Albedo_{index}.png')
        image.file_format='PNG'
        image.save()
        tree.nodes.remove(emission)
        tree.nodes.remove(vertex)
        principled=tree.nodes.new('ShaderNodeBsdfPrincipled')
        principled.inputs['Roughness'].default_value=0.65
        tree.links.new(texture.outputs['Color'],principled.inputs['Base Color'])
        tree.links.new(principled.outputs['BSDF'],out.inputs['Surface'])

def prepare_geometry_only():
    """Useful editable UVs and neutral shader; never manufacture albedo maps."""
    material=bpy.data.materials.new('Forge3D_NeutralGeometry')
    material.use_nodes=True
    bsdf=material.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value=(0.5,0.5,0.5,1)
    bsdf.inputs['Metallic'].default_value=0
    bsdf.inputs['Roughness'].default_value=0.65
    for obj in meshes():
        bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
        if not obj.data.uv_layers:
            bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.uv.smart_project(angle_limit=math.radians(66),island_margin=0.015)
            bpy.ops.object.mode_set(mode='OBJECT')
        obj.data.materials.clear();obj.data.materials.append(material)

def recalculate_orientation(data):
    # UV seams split glTF vertices. Orient a temporary geometric topology,
    # then transfer only face flips; preserve every position and UV corner.
    geometry=bmesh.new()
    try:
        geometry.from_mesh(data)
        original=geometry.faces.layers.int.new('Forge3D_OriginalFace')
        for index,face in enumerate(geometry.faces):face[original]=index
        bmesh.ops.remove_doubles(geometry,verts=list(geometry.verts),dist=1e-7)
        bmesh.ops.recalc_face_normals(geometry,faces=list(geometry.faces))
        geometry.normal_update()
        for face in geometry.faces:
            polygon=data.polygons[face[original]]
            if face.normal.dot(polygon.normal)<0:polygon.flip()
        data.update()
        data.normals_split_custom_set([(0.,0.,0.)]*len(data.loops))
        data.update()
    finally:geometry.free()

def transform(options):
    operation=options['operation']
    select_all_meshes()
    if operation=='center':
        center()
    elif operation=='apply_transforms':
        bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
    elif operation=='fix_scale':
        height=stats()['dimensions'][2]
        factor=options.get('height',1)/max(height,1e-9)
        for obj in meshes():
            obj.location*=factor
            obj.scale*=factor
        bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
    elif operation in ['decimate','triangulate']:
        for obj in meshes():
            bpy.context.view_layer.objects.active=obj
            if operation=='decimate':
                # glTF duplicates positions for discontinuous normals/UVs.
                # Reconnect geometric neighbors before edge-collapse; UV data
                # lives on face loops and remains independent across seams.
                geometry=bmesh.new()
                geometry.from_mesh(obj.data)
                bmesh.ops.remove_doubles(geometry,verts=list(geometry.verts),dist=1e-7)
                geometry.to_mesh(obj.data)
                geometry.free()
            modifier=obj.modifiers.new('Forge3D', 'DECIMATE' if operation=='decimate' else 'TRIANGULATE')
            if operation=='decimate':
                modifier.ratio=options.get('ratio',0.5)
            bpy.ops.object.modifier_apply(modifier=modifier.name)
            if operation=='decimate':
                geometry=bmesh.new()
                geometry.from_mesh(obj.data)
                loose=[vertex for vertex in geometry.verts if not vertex.link_faces]
                bmesh.ops.delete(geometry,geom=loose,context='VERTS')
                geometry.to_mesh(obj.data)
                geometry.free()
    elif operation=='recalculate_normals':
        for obj in meshes():recalculate_orientation(obj.data)
    elif operation not in ['validate','inspect_materials']:
        raise ValueError('Operation not allowed')
    bpy.context.view_layer.update()

def save_glb(path):
    select_all_meshes()
    temporary=path.with_name(path.stem+'.temp.glb')
    bpy.ops.export_scene.gltf(filepath=str(temporary),export_format='GLB',use_selection=True,export_yup=True)
    temporary.replace(path)

def render_views(directory,unlit=False,clay=False,front_axis='x',resolution=384,opposite_side=False,normalize_light=False):
    scene=bpy.context.scene
    scene.render.engine='CYCLES'
    scene.cycles.samples=8
    scene.cycles.seed=42
    if resolution not in [384,768,1024]:raise ValueError('Resolução QA inválida.')
    scene.render.resolution_x=scene.render.resolution_y=resolution
    scene.render.resolution_percentage=100
    scene.view_settings.view_transform='Standard'
    scene.view_settings.look='None'
    scene.view_settings.exposure=0
    scene.view_settings.gamma=1
    if clay:
        material=bpy.data.materials.new('QA_NeutralGeometry')
        material.use_nodes=True
        bsdf=material.node_tree.nodes.get('Principled BSDF')
        bsdf.inputs['Base Color'].default_value=(0.5,0.5,0.5,1)
        bsdf.inputs['Metallic'].default_value=0
        bsdf.inputs['Roughness'].default_value=0.65
        for obj in meshes():
            obj.data.materials.clear();obj.data.materials.append(material)
            for polygon in obj.data.polygons:polygon.material_index=0
    if unlit:
        for material in bpy.data.materials:
            if not material.use_nodes:continue
            tree=material.node_tree
            bsdf=next((node for node in tree.nodes if node.type=='BSDF_PRINCIPLED'),None)
            output=next((node for node in tree.nodes if node.type=='OUTPUT_MATERIAL'),None)
            if bsdf and output:
                emission=tree.nodes.new('ShaderNodeEmission')
                color=bsdf.inputs['Base Color'];alpha=bsdf.inputs['Alpha']
                if color.is_linked:tree.links.new(color.links[0].from_socket,emission.inputs['Color'])
                else:emission.inputs['Color'].default_value=color.default_value
                surface=emission.outputs[0]
                if alpha.is_linked or alpha.default_value<.999:
                    transparent=tree.nodes.new('ShaderNodeBsdfTransparent');mix=tree.nodes.new('ShaderNodeMixShader')
                    if alpha.is_linked:tree.links.new(alpha.links[0].from_socket,mix.inputs[0])
                    else:mix.inputs[0].default_value=alpha.default_value
                    tree.links.new(transparent.outputs[0],mix.inputs[1]);tree.links.new(surface,mix.inputs[2]);surface=mix.outputs[0]
                tree.links.new(surface,output.inputs['Surface'])
    scene.world.use_nodes=True
    scene.world.node_tree.nodes['Background'].inputs[0].default_value=(0.16,0.16,0.16,1)
    info=stats()
    target=(Vector(info['bounds_min'])+Vector(info['bounds_max']))/2
    radius=max(info['dimensions'])*2.3
    camera_data=bpy.data.cameras.new('QA_Camera')
    camera=bpy.data.objects.new('QA_Camera',camera_data)
    scene.collection.objects.link(camera)
    scene.camera=camera
    light_data=bpy.data.lights.new('QA_Light','AREA')
    scale=max(info['dimensions'])
    light_data.energy=600*(scale**2 if clay or normalize_light else 1)
    light_data.shape='DISK'
    light_data.size=5*(scale if clay else 1)
    light=bpy.data.objects.new('QA_Light',light_data)
    scene.collection.objects.link(light)
    light_direction=(-3,-2,4) if (clay or normalize_light) and front_axis=='negative_y' else (2,-3,4)
    light.location=target+Vector(light_direction)*scale
    # TripoSR conditioning camera is +X (up +Z). Keep front/side labels honest.
    directions=[('front',(1,0,0.15)),('side',(0,-1,0.15)),('rear',(-1,0,0.15)),('three_quarter',(1,-1,0.35))]
    if front_axis=='negative_y':directions=[('front',(0,-1,0.15)),('side',(-1,0,0.15)),('rear',(0,1,0.15)),('three_quarter',(-1,-1,0.35))]
    if opposite_side:directions.append(('side_opposite',(1,0,0.15) if front_axis=='negative_y' else (0,1,0.15)))
    for name,direction in directions:
        camera.location=target+Vector(direction).normalized()*radius
        camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
        scene.render.filepath=str(directory/f'qa_{name}.png')
        bpy.ops.render.render(write_still=True)

def export_fbx(directory,options=None):
    options=options or {}
    models=directory/'Models'
    textures=directory/'Textures'
    models.mkdir(parents=True,exist_ok=True)
    textures.mkdir(parents=True,exist_ok=True)
    used={}
    for obj in meshes():
        for material in obj.data.materials:
            if not material or not material.use_nodes:continue
            for node in material.node_tree.nodes:
                if node.type!='TEX_IMAGE' or not node.image:continue
                channel='Data'
                for link in node.outputs['Color'].links:
                    if link.to_node.type=='NORMAL_MAP' or link.to_socket.name=='Normal':channel='Normal'
                    elif link.to_socket.name=='Base Color':channel='BaseColor'
                    elif link.to_socket.name=='Roughness':channel='Roughness'
                    elif link.to_socket.name=='Metallic':channel='Metallic'
                used[node.image]=channel
    for index,(image,channel) in enumerate(used.items()):
        if image.type=='IMAGE' and image.size[0]>0:
            target=str((textures/f'{channel}_{index}.png').resolve())
            image.filepath_raw=target
            image.file_format='PNG'
            image.save()
            # OBJ reads the packed image's original path when it remains packed.
            # The actual PNG has been saved, so remove only the in-memory pack.
            if image.packed_file:image.unpack(method='REMOVE')
            image.filepath=target
    before=stats()
    select_all_meshes()
    if options.get('include_glb',True):save_glb(models/'Model.glb')
    if options.get('include_obj',True):
        bpy.ops.wm.obj_export(filepath=str(models/'Model.obj'),export_selected_objects=True,forward_axis='NEGATIVE_Z',up_axis='Y',export_triangulated_mesh=True,export_materials=True,path_mode='RELATIVE')
    path=models/'Model.fbx'
    bpy.context.scene.unit_settings.system='METRIC'
    bpy.context.scene.unit_settings.scale_length=1
    bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH'},axis_forward='-Z',axis_up='Y',apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',use_mesh_modifiers=True,use_triangles=True,mesh_smooth_type='FACE',path_mode='RELATIVE',add_leaf_bones=False,bake_anim=False)
    if path.stat().st_size<100:
        raise RuntimeError('Empty FBX export')
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.fbx(filepath=str(path))
    after=stats()
    save_glb(directory.parent/'fbx_reimport.glb')
    if before['triangles']!=after['triangles'] or before['uv_meshes']!=after['uv_meshes']:
        raise RuntimeError('FBX reimport lost geometry or UV layers')
    if any(abs(a-b)>max(0.001,abs(a)*0.01) for a,b in zip(before['dimensions'],after['dimensions'])):
        raise RuntimeError('FBX reimport scale mismatch')
    return {'passed':True,'before':before,'after':after,'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'axes':{'forward':'-Z','up':'Y'},'units':'meters','external_textures':[p.name for p in textures.glob('*.png')]}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--input',required=True)
    parser.add_argument('--output',required=True)
    parser.add_argument('--mode',choices=['prepare','transform','export','compare'],required=True)
    parser.add_argument('--options',required=True)
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    directory=Path(args.output).resolve()
    directory.mkdir(parents=True,exist_ok=True)
    options=json.loads(Path(args.options).read_text(encoding='utf-8-sig'))
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=str(Path(args.input).resolve()))
    before=stats()
    warnings=[]
    if args.mode=='prepare':
        # TripoSR raw trimesh GLB contains Z-up coordinates. glTF import assumes
        # Y-up, so undo that conversion before exporting canonical Y-up GLB.
        raw_up=options.get('raw_up','Z')
        if raw_up not in ['Y','Z']:raise ValueError('Convenção de eixos inválida.')
        if raw_up=='Z':
            rotation=Matrix.Rotation(-math.pi/2,4,'X')
            for obj in meshes():obj.matrix_world=rotation@obj.matrix_world
        select_all_meshes()
        bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
        bpy.context.view_layer.update()
        center()
        if options.get('geometry_only'):prepare_geometry_only()
        else:bake_colors(directory/'textures',options.get('texture_resolution',1024))
        save_glb(directory/'model.glb')
        render_views(directory,front_axis=options.get('front_axis','x'))
    elif args.mode=='transform':
        if options['operation']=='game_ready':
            from blender.game_ready import build_game_ready
            bake=build_game_ready(directory,options);warnings+=bake['warnings']
        else:transform(options)
        save_glb(directory/'model.glb')
        if options['operation']=='decimate':
            warnings.append('Decimation pode alterar detalhes e distorcer UVs. Original preservado; não equivale a retopologia para animação.')
    elif args.mode=='export':
        validation=export_fbx(directory/'Forge3D_Asset',options)
        (directory/'fbx_validation.json').write_text(json.dumps(validation,indent=2),encoding='utf-8')
    elif args.mode=='compare':
        # Input here is canonical processed glTF, whose Y-up conversion is valid.
        render_views(directory,options.get('unlit',False),options.get('clay',False),options.get('front_axis','x'),options.get('render_resolution',384),options.get('opposite_side',False),options.get('normalize_light',False))
    after=stats()
    after['integrity']=integrity()
    for result in after['integrity']:
        if result.get('orientation')=='inward_closed':warnings.append('Malha fechada com faces voltadas para dentro; a geometria pode parecer oca em visualizadores com culling. Gere novamente ou revise a orientação das faces.')
        if result['degenerate_triangles']:warnings.append(f"{result['degenerate_triangles']} triângulos de área quase zero nesta versão; confira o relatório. RAW preservado.")
        if result['nonmanifold_edges']:warnings.append(f"{result['nonmanifold_edges']} arestas não manifold detectadas; avalie antes de colisão/edição.")
        if result['connected_components']>1:warnings.append(f"{result['connected_components']} componentes desconectados; confira partes soltas nas vistas.")
    report={'before':before,'after':after,'warnings':warnings,'blender_version':bpy.app.version_string}
    (directory/('comparison_report.json' if args.mode=='compare' else 'mesh_report.json')).write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('FORGE3D_RESULT '+json.dumps(report),flush=True)

if __name__=='__main__':
    main()
