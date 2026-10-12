"""Actual high-to-low baking acceptance fixture, not an AI result."""
import sys,json,math
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
args=sys.argv[sys.argv.index('--')+1:];out=Path(args[0]).resolve();out.mkdir(parents=True,exist_ok=True);resolution=int(args[1]) if len(args)>1 else 1024
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.ops.mesh.primitive_uv_sphere_add(segments=96,ring_count=64)
obj=bpy.context.object
for vertex in obj.data.vertices:
    direction=vertex.co.normalized();wave=.025*math.sin(direction.x*22)*math.cos(direction.y*17)*math.cos(direction.z*12)
    vertex.co*=1+wave
for polygon in obj.data.polygons:polygon.use_smooth=True
material=bpy.data.materials.new('ActualBaseColor');material.use_nodes=True;material.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value=(.55,.13,.035,1);obj.data.materials.append(material)
from blender.pipeline import save_glb
save_glb(out/'high_original.glb')
from blender.game_ready import build_game_ready
report=build_game_ready(out,{'target_triangles':2000,'texture_resolution':resolution,'bake_normal':True})
save_glb(out/'model.glb')
assert report['source_triangles']>report['actual_triangles']
assert report['actual_triangles']<=2100
assert report['normal_bake']['performed'] and report['normal_bake']['normal_variation']>.01
assert (out/'high_original.glb').is_file() and (out/('textures/Normal_'+str(resolution)+'.png')).is_file()
(out/'test_acceptance.json').write_text(json.dumps({'passed':True,'report':report},indent=2),encoding='utf-8')
print('ACTUAL_HIGH_TO_LOW_NORMAL_BAKE_PASS',flush=True)
