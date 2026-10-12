"""Disposable controlled research fixture; run with Blender, not product code."""
import bpy
import json
import sys
from pathlib import Path
from mathutils import Vector

dest = Path(sys.argv[sys.argv.index('--') + 1])
dest.mkdir(parents=True, exist_ok=True)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

def box(name, location, dimensions):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return obj

parts = [box('seat', (0, 0, .72), (.88, .82, .12))]
for x in [-.34, .34]:
    for y in [-.30, .30]:
        parts.append(box('leg', (x, y, .34), (.12, .12, .68)))
    parts.append(box('back_post', (x, .30, 1.14), (.12, .12, .96)))
for z in [1.17, 1.52]:
    parts.append(box('back_slat', (0, .30, z), (.72, .12, .15)))
base = parts[0]
for obj in parts[1:]:
    bpy.context.view_layer.objects.active = base
    mod = base.modifiers.new('exact_union', 'BOOLEAN')
    mod.operation = 'UNION'
    mod.solver = 'EXACT'
    mod.object = obj
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(obj, do_unlink=True)
bpy.context.view_layer.objects.active = base
bevel = base.modifiers.new('rounded_edges', 'BEVEL')
bevel.width = .014
bevel.segments = 2
bpy.ops.object.modifier_apply(modifier=bevel.name)
base.name = 'ProceduralChairGroundTruth'
mat = bpy.data.materials.new('WarmWood')
mat.use_nodes = True
mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (.48, .22, .065, 1)
mat.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = .65
base.data.materials.append(mat)
bpy.ops.object.select_all(action='DESELECT')
base.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(island_margin=.02)
bpy.ops.object.mode_set(mode='OBJECT')
bpy.ops.export_scene.gltf(filepath=str(dest/'ground_truth.glb'), export_format='GLB', use_selection=True)
bpy.ops.export_scene.fbx(filepath=str(dest/'ground_truth.fbx'), use_selection=True, object_types={'MESH'}, axis_forward='-Z', axis_up='Y', bake_anim=False, add_leaf_bones=False)
base.data.calc_loop_triangles()

scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.samples = 24
scene.cycles.seed = 42
scene.render.resolution_x = scene.render.resolution_y = 512
scene.render.resolution_percentage = 100
scene.render.film_transparent = True
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGBA'
scene.view_settings.view_transform = 'Standard'
scene.world.use_nodes = True
scene.world.node_tree.nodes['Background'].inputs[0].default_value = (.4, .4, .4, 1)
scene.world.node_tree.nodes['Background'].inputs[1].default_value = .6
light_data = bpy.data.lights.new('softbox', 'AREA')
light_data.energy = 350
light_data.size = 4
light = bpy.data.objects.new('softbox', light_data)
scene.collection.objects.link(light)
light.location = (-3, -4, 4)
camera = bpy.data.objects.new('camera', bpy.data.cameras.new('camera'))
scene.collection.objects.link(camera)
scene.camera = camera
camera.data.type = 'ORTHO'
camera.data.ortho_scale = 1.92
target = Vector((0, 0, .81))
for name, direction in [('front', (0, -4, .12)), ('three_quarter', (3, -4, 2.2)), ('rear', (0, 4, .12)), ('side', (4, 0, .12))]:
    camera.location = target + Vector(direction)
    camera.rotation_euler = (target-camera.location).to_track_quat('-Z', 'Y').to_euler()
    scene.render.filepath = str(dest/(name+'.png'))
    bpy.ops.render.render(write_still=True)
(dest/'fixture.json').write_text(json.dumps({'source':'assistant-authored deterministic Blender procedural model, no neural generator', 'triangles':len(base.data.loop_triangles), 'dimensions':list(base.dimensions), 'reference_resolution':512, 'camera':'orthographic', 'ground_truth_available':True, 'note':'one controlled chair; no population-level quality conclusion'}, indent=2), encoding='utf-8')
print('FIXTURE_CREATED', flush=True)
