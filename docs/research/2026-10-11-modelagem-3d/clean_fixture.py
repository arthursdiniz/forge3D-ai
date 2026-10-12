"""Clean numerical degenerates in a NEW GT file; reference PNGs stay immutable."""
import bpy,bmesh,json,sys
from pathlib import Path
out=Path(sys.argv[sys.argv.index('--')+1])
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(out/'ground_truth.glb'))
for obj in bpy.context.scene.objects:
    if obj.type!='MESH':continue
    bm=bmesh.new();bm.from_mesh(obj.data)
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-6)
    bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=1e-7)
    bad=[face for face in bm.faces if face.calc_area()<1e-12]
    if bad:bmesh.ops.delete(bm,geom=bad,context='FACES_ONLY')
    loose=[vertex for vertex in bm.verts if not vertex.link_faces]
    if loose:bmesh.ops.delete(bm,geom=loose,context='VERTS')
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    for face in bm.faces:face.smooth=False
    bm.to_mesh(obj.data);bm.free();obj.data.update()
    obj.data.calc_loop_triangles()
    report={'triangles':len(obj.data.loop_triangles),'vertices':len(obj.data.vertices),'dimensions':list(obj.dimensions),'source':'ground_truth.glb','method':'numeric weld + dissolve degenerates + remove loose vertices; no new boolean/bevel','reference_pngs_modified':False}
bpy.ops.object.select_all(action='DESELECT')
for obj in bpy.context.scene.objects:
    if obj.type=='MESH':obj.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(out/'ground_truth_clean.glb'),export_format='GLB',use_selection=True)
bpy.ops.export_scene.fbx(filepath=str(out/'ground_truth_clean.fbx'),use_selection=True,object_types={'MESH'},axis_forward='-Z',axis_up='Y',bake_anim=False,add_leaf_bones=False)
(out/'cleanup.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('NEW_CLEAN_GT_EXPORTED '+json.dumps(report),flush=True)
