"""Trusted Blender fixture: own static FBX with one embedded albedo."""
import sys
from pathlib import Path
import bpy
target=Path(sys.argv[sys.argv.index('--')+1]).resolve()
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.ops.mesh.primitive_cube_add()
obj=bpy.context.object
image=bpy.data.images.new('EmbeddedAlbedo',8,8)
image.pixels=[210/255,40/255,20/255,1]*64
image.filepath_raw=str(target.parent/'embedded-albedo.png');image.file_format='PNG';image.save();image.pack()
material=bpy.data.materials.new('Embedded');material.use_nodes=True
node=material.node_tree.nodes.new('ShaderNodeTexImage');node.image=image
material.node_tree.links.new(node.outputs['Color'],material.node_tree.nodes.get('Principled BSDF').inputs['Base Color'])
obj.data.materials.append(material)
bpy.ops.export_scene.fbx(filepath=str(target),use_selection=True,object_types={'MESH'},path_mode='COPY',embed_textures=True,bake_anim=False,add_leaf_bones=False)
Path(image.filepath_raw).unlink()
