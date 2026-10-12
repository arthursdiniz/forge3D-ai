"""Owned procedural QA references, explicitly not AI-generated character results."""
import argparse
import json
import math
import sys
from pathlib import Path
import bpy
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

CASES=['a_pose','anime_hair','bulky_clothing','symmetric','asymmetric_accessory','dynamic','multiview']

def material(name,color):
    result=bpy.data.materials.new(name);result.use_nodes=True
    node=result.node_tree.nodes.get('Principled BSDF');node.inputs['Base Color'].default_value=(*color,1);node.inputs['Roughness'].default_value=.7
    return result

def ellipsoid(name,position,scale,mat):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24,ring_count=12,location=position)
    obj=bpy.context.object;obj.name=name;obj.scale=scale;obj.data.materials.append(mat)
    for polygon in obj.data.polygons:polygon.use_smooth=True
    return obj

def capsule(name,a,b,radius,mat):
    a=Vector(a);b=Vector(b);direction=b-a
    bpy.ops.mesh.primitive_cylinder_add(vertices=20,radius=radius,depth=direction.length,location=(a+b)/2)
    obj=bpy.context.object;obj.name=name;obj.rotation_euler=direction.to_track_quat('Z','Y').to_euler();obj.data.materials.append(mat)
    for polygon in obj.data.polygons:polygon.use_smooth=True
    for index,point in enumerate([a,b]):ellipsoid(name+'_joint'+str(index),point,(radius,)*3,mat)

def build(case):
    skin=material('skin',(.62,.36,.20));shirt=material('shirt',(.06,.19,.42));cloth=material('shorts',(.06,.08,.10));hair=material('hair',(.6,.18,.025));white=material('shoes',(.55,.58,.6));eyes=material('eyes',(.01,.01,.015))
    joints={'left_shoulder':(.21,0,1.36),'right_shoulder':(-.21,0,1.36),'left_elbow':(.36,0,1.15),'right_elbow':(-.36,0,1.15),'left_wrist':(.47,0,.93),'right_wrist':(-.47,0,.93),'left_hip':(.12,0,.86),'right_hip':(-.12,0,.86),'left_knee':(.14,0,.48),'right_knee':(-.14,0,.48),'left_ankle':(.15,0,.12),'right_ankle':(-.15,0,.12),'nose':(0,-.117,1.60),'left_eye':(.045,-.099,1.65),'right_eye':(-.045,-.099,1.65),'left_ear':(.12,0,1.61),'right_ear':(-.12,0,1.61),'head_top':(0,0,1.77),'chin':(0,-.075,1.44),'neck':(0,0,1.43),'pelvis':(0,0,.86),'head_center':(0,0,1.61)}
    if case=='dynamic':joints.update(left_elbow=(.33,-.04,1.52),left_wrist=(.34,-.04,1.77),right_knee=(-.20,-.10,.47),right_ankle=(-.33,-.03,.10))
    torso_scale=(.23,.145,.28) if case!='bulky_clothing' else (.31,.22,.30)
    ellipsoid('body_torso',(0,0,1.12),torso_scale,shirt);ellipsoid('body_hips',(0,0,.88),(.20,.14,.17),cloth)
    capsule('neck',(0,0,1.34),(0,0,1.48),.055,skin)
    ellipsoid('head',(0,0,1.61),(.125,.108,.17),skin);ellipsoid('nose',joints['nose'],(.022,.025,.027),skin)
    for side in ['left','right']:
        ellipsoid(side+'_eye',joints[side+'_eye'],(.018,.011,.021),eyes)
        ellipsoid(side+'_ear',joints[side+'_ear'],(.025,.027,.045),skin)
        capsule(side+'_upper_arm',joints[side+'_shoulder'],joints[side+'_elbow'],.071,shirt)
        capsule(side+'_forearm',joints[side+'_elbow'],joints[side+'_wrist'],.047,skin)
        wrist=Vector(joints[side+'_wrist']);hand=wrist+Vector((.013 if side=='left' else -.013,0,-.075))
        ellipsoid(side+'_hand',hand,(.046,.027,.075),skin)
        for index in range(4):
            point=hand+Vector(((index-1.5)*.019,-.004,-.060));capsule(side+'_finger'+str(index),point,point+Vector((0,0,-.055)),.009,skin)
        joints[side+'_index']=tuple(hand+Vector((.012,-.003,-.09)));joints[side+'_pinky']=tuple(hand+Vector((-.032,-.003,-.08)));joints[side+'_thumb']=tuple(hand+Vector((.04,-.005,-.018)))
        capsule(side+'_thigh',joints[side+'_hip'],joints[side+'_knee'],.088,cloth)
        capsule(side+'_shin',joints[side+'_knee'],joints[side+'_ankle'],.060,skin)
        ankle=Vector(joints[side+'_ankle']);foot=ankle+Vector((0,-.075,-.07))
        ellipsoid(side+'_shoe',foot,(.092,.155,.076),white)
        joints[side+'_heel']=tuple(foot+Vector((0,.10,0)));joints[side+'_foot_index']=tuple(foot+Vector((0,-.13,0)))
    ellipsoid('hair_cap',(0,.015,1.72),(.132,.116,.12),hair)
    if case in ['anime_hair','asymmetric_accessory']:
        for index in range(14):
            angle=index*math.tau/14;position=Vector((math.cos(angle)*.09,math.sin(angle)*.08,1.76))
            bpy.ops.mesh.primitive_cone_add(vertices=12,radius1=.035,radius2=.001,depth=.13,location=position)
            obj=bpy.context.object;obj.name='hair_spike'+str(index);obj.rotation_euler=Vector((math.cos(angle),math.sin(angle),1.5)).to_track_quat('Z','Y').to_euler();obj.data.materials.append(hair)
    if case=='asymmetric_accessory':
        accessory=material('asymmetric_accessory',(.40,.03,.025))
        ellipsoid('intentional_left_bag',(.34,.10,.98),(.09,.10,.15),accessory)
    return joints

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    root=Path(args.output).resolve()
    if root.exists():raise RuntimeError('Preserve prior fixtures; choose a new output directory.')
    root.mkdir(parents=True)
    for case in CASES:
        bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
        joints=build(case);directory=root/case;directory.mkdir()
        for obj in [obj for obj in bpy.context.scene.objects if obj.type=='MESH']:
            bpy.context.view_layer.objects.active=obj;obj.select_set(True);bpy.ops.object.transform_apply(location=False,rotation=True,scale=True);obj.select_set(False)
        bpy.ops.export_scene.gltf(filepath=str(directory/'ground_truth.glb'),export_format='GLB',export_yup=True)
        scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=16;scene.cycles.seed=42;scene.render.film_transparent=True
        scene.render.resolution_x=640;scene.render.resolution_y=768;scene.render.resolution_percentage=100
        scene.view_settings.view_transform='Standard';scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.6,.6,.6,1)
        bpy.ops.object.light_add(type='AREA',location=(-3,-4,5));light=bpy.context.object;light.data.energy=350;light.data.size=5
        light.rotation_euler=(Vector((0,0,1))-light.location).to_track_quat('-Z','Y').to_euler()
        bpy.ops.object.camera_add();camera=bpy.context.object;camera.data.type='ORTHO';camera.data.ortho_scale=2.25;scene.camera=camera
        references={}
        for name,direction in [('front',(0,-1,0)),('left',(1,0,0)),('back',(0,1,0)),('right',(-1,0,0)),('three_quarter',(.7,-1,.2))]:
            camera.location=Vector((0,0,.97))+Vector(direction).normalized()*4
            camera.rotation_euler=(Vector((0,0,.97))-camera.location).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(directory/(name+'.png'))
            bpy.ops.render.render(write_still=True)
            if name=='front':
                for key,value in joints.items():
                    point=world_to_camera_view(scene,camera,Vector(value));references[key]={'x':float(point.x),'y':float(1-point.y),'source':'manual','reviewed':True,'provenance':'known procedural scene projection'}
        metadata={'fixture_only':True,'ai_generated':False,'reference_license':'CC0-1.0; procedural QA images/meshes created for this project','category':'anime' if case=='anime_hair' else 'cartoon','pose':'dynamic' if case=='dynamic' else 'a_pose','view':'front','landmarks':references,'intentional_asymmetry':case=='asymmetric_accessory','intentional_separate_geometry':['hair','clothes','shoes','accessory']}
        (directory/'fixture.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
        print('OWNED_CHARACTER_FIXTURE '+case,flush=True)
    (root/'LICENSE.txt').write_text('CC0-1.0: procedural QA reference images and meshes authored for Forge3D. These are test inputs/ground truths, not generated AI results.',encoding='utf-8')

if __name__=='__main__':main()
