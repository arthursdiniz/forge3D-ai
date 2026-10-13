"""Run in Blender: albedo QA must follow Base Color, never the first image node."""
import sys
from pathlib import Path
import bpy
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from blender.pipeline import render_views
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.ops.mesh.primitive_cube_add()
material=bpy.data.materials.new('TestNormalFirst');material.use_nodes=True
nodes=material.node_tree.nodes;links=material.node_tree.links;bsdf=nodes.get('Principled BSDF')
normal=nodes.new('ShaderNodeTexImage');normal.image=bpy.data.images.new('FirstNormal',width=16,height=16);normal.image.pixels[:]=[.5,.5,1,1]*256
normal_node=nodes.new('ShaderNodeNormalMap');links.new(normal.outputs['Color'],normal_node.inputs['Color']);links.new(normal_node.outputs['Normal'],bsdf.inputs['Normal'])
albedo=nodes.new('ShaderNodeTexImage');albedo.image=bpy.data.images.new('ActualAlbedo',width=16,height=16);albedo.image.pixels[:]=[1,0,0,1]*256;links.new(albedo.outputs['Color'],bsdf.inputs['Base Color'])
bpy.context.object.data.materials.append(material)
directory=ROOT/'data/texture-engine-20261012/unlit-regression';directory.mkdir(parents=True,exist_ok=True)
render_views(directory,unlit=True,front_axis='negative_y')
image=bpy.data.images.load(str(directory/'qa_front.png'));pixels=np.asarray(image.pixels[:]).reshape(384,384,4);center=pixels[180:204,180:204,:3].mean(axis=(0,1))
assert center[0]>.8 and center[2]<.1,('Albedo QA selected normal image',center)
print('TRUE_BASE_COLOR_UNLIT_PASS',flush=True)
