"""Trusted importer with all image lookup confined to staged local sidecars."""
import argparse
import json
import sys
from pathlib import Path
import bpy

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--input',required=True);parser.add_argument('--output',required=True);args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    source=Path(args.input).resolve();directory=Path(args.output).resolve();allowed=source.parent
    import bpy_extras.image_utils as images
    original=images.load_image
    def guarded(imagepath,dirname='',*arguments,**kwargs):
        # FBX records publisher-specific absolute paths. Resolve only the exact
        # basename among staged sidecars, never open the recorded external path.
        candidate=allowed/Path(imagepath).name
        candidate=candidate.resolve()
        if not candidate.is_relative_to(allowed):raise ValueError('External FBX/OBJ image paths are not supported; supply local sidecars.')
        if not candidate.is_file() and not kwargs.get('place_holder',False):raise ValueError('Missing local image sidecar.')
        # FBX packs embedded bytes into a placeholder after this call. Restrict
        # all lookup variants to the staged path even when no sidecar exists.
        kwargs.update(recursive=False,ncase_cmp=False)
        return original(str(candidate),str(allowed),*arguments,**kwargs)
    images.load_image=guarded
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    extension=source.suffix.lower()
    if extension in ['.glb','.gltf']:bpy.ops.import_scene.gltf(filepath=str(source))
    elif extension=='.obj':bpy.ops.wm.obj_import(filepath=str(source),forward_axis='NEGATIVE_Z',up_axis='Y')
    elif extension=='.fbx':bpy.ops.import_scene.fbx(filepath=str(source),use_image_search=False,use_anim=False)
    else:raise ValueError('Unsupported static format.')
    if any(obj.type=='ARMATURE' or obj.animation_data or (obj.type=='MESH' and obj.data.shape_keys) for obj in bpy.context.scene.objects):raise ValueError('Static meshes only; remove animation/rig/morphs.')
    meshes=[obj for obj in bpy.context.scene.objects if obj.type=='MESH']
    if not meshes or sum(len(obj.data.polygons) for obj in meshes)>2_000_000:raise ValueError('Empty mesh or more than 2 million faces.')
    for image in bpy.data.images:
        if image.source=='FILE' and image.filepath and not image.packed_file:
            path=Path(bpy.path.abspath(image.filepath)).resolve()
            if not path.is_relative_to(allowed):raise ValueError('Image path outside staged resources.')
            if not path.is_file():raise ValueError('Missing local image sidecar or embedded FBX image.')
    for obj in meshes:
        if len(obj.data.uv_layers)>1:raise ValueError('Static single-UV meshes only; secondary UVs need explicit preservation support.')
        if any(not all(__import__('math').isfinite(c) for c in v.co) for v in obj.data.vertices):raise ValueError('Nonfinite vertices.')
    bpy.ops.object.select_all(action='DESELECT')
    for obj in meshes:obj.select_set(True)
    bpy.context.view_layer.objects.active=meshes[0]
    bpy.ops.export_scene.gltf(filepath=str(directory/'model.glb'),export_format='GLB',use_selection=True,export_normals=True,export_yup=True,export_animations=False)
    (directory/'import.json').write_text(json.dumps({'static':True,'format':extension,'source_preserved':True,'meshes':len(meshes),'blender':bpy.app.version_string,'image_lookup':'staged resources only','axes':'canonical glTF Y-up; user chooses front axis'},indent=2),encoding='utf-8')

if __name__=='__main__':main()
