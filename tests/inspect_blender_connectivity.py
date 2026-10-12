import bpy
import bmesh
import sys
from pathlib import Path

source=sys.argv[sys.argv.index('--')+1]
for merge in [False,True]:
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=source,merge_vertices=merge)
    for obj in bpy.context.scene.objects:
        if obj.type!='MESH':continue
        mesh=bmesh.new()
        mesh.from_mesh(obj.data)
        boundary=sum(edge.is_boundary for edge in mesh.edges)
        loose=sum(not vertex.link_faces for vertex in mesh.verts)
        print('CONNECTIVITY',merge,len(mesh.verts),len(mesh.faces),boundary,loose,flush=True)
        mesh.free()
