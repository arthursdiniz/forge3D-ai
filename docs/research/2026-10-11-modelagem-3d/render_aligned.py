"""Shared camera and neutral material: do not let textures hide shape errors."""
import bpy
import sys
from pathlib import Path
from mathutils import Vector

out=Path(sys.argv[sys.argv.index('--')+1])
names=['ground_truth','sg_front_baseline','sg_front_quality512','sg_three_quarter','sr_three_quarter_neural','sg_best_low']
for name in names:
    source=out/'aligned'/(name+'.glb')
    if not source.exists():continue
    dest=out/'comparison'/name
    dest.mkdir(parents=True,exist_ok=True)
    if all((dest/(view+'.png')).exists() for view in ['front','side','rear','three_quarter']):
        continue
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=str(source))
    neutral=bpy.data.materials.new('neutral_'+name)
    neutral.use_nodes=True
    bsdf=neutral.node_tree.nodes['Principled BSDF']
    bsdf.inputs['Base Color'].default_value=(.48,.52,.57,1)
    bsdf.inputs['Roughness'].default_value=.72
    for obj in bpy.context.scene.objects:
        if obj.type=='MESH':
            obj.data.materials.clear()
            obj.data.materials.append(neutral)
    scene=bpy.context.scene
    scene.render.engine='CYCLES'
    scene.cycles.samples=12
    scene.cycles.seed=42
    scene.render.resolution_x=scene.render.resolution_y=384
    scene.render.resolution_percentage=100
    scene.render.film_transparent=False
    scene.view_settings.view_transform='Standard'
    scene.world.use_nodes=True
    scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.065,.078,.095,1)
    scene.world.node_tree.nodes['Background'].inputs[1].default_value=.7
    cam=bpy.data.objects.new('camera',bpy.data.cameras.new('camera'))
    scene.collection.objects.link(cam)
    scene.camera=cam
    cam.data.type='ORTHO'
    cam.data.ortho_scale=1.32
    light=bpy.data.objects.new('softbox',bpy.data.lights.new('softbox','AREA'))
    scene.collection.objects.link(light)
    light.data.energy=180
    light.data.size=4
    light.location=(-2,-3,4)
    for view,direction in [('front',(0,-3,.08)),('side',(3,0,.08)),('rear',(0,3,.08)),('three_quarter',(3,-4,2))]:
        cam.location=Vector(direction)
        cam.rotation_euler=(-cam.location).to_track_quat('-Z','Y').to_euler()
        scene.render.filepath=str(dest/(view+'.png'))
        bpy.ops.render.render(write_still=True)
    print('ALIGNED_VIEWS_READY '+name,flush=True)
