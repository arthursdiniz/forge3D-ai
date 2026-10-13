"""Bounded static asset resources. Never accept arbitrary external filesystem URIs."""
import json
import re
import struct
from urllib.parse import unquote

def safe_name(name):
    if not name or len(name)>160 or name in ['.','..'] or any(c in name for c in '/\\:<>|"*?') or name.startswith('.') or name.endswith((' ','.')) or any(ord(c)<32 for c in name):raise ValueError('Use simple local filenames without paths.')
    if name.split('.')[0].upper() in {'CON','PRN','AUX','NUL',*(f'COM{i}' for i in range(10)),*(f'LPT{i}' for i in range(10))}:raise ValueError('Reserved filename.')
    return name

def validate_resources(name,content,sidecars):
    safe_name(name)
    extension=name.rsplit('.',1)[-1].lower()
    if extension not in ['glb','gltf','obj','fbx']:raise ValueError('Import supports static GLB/GLTF/OBJ/FBX only.')
    names={key.casefold() for key in sidecars}
    def uri(value):
        if value.startswith('data:'):
            if not re.match(r'^data:(application/octet-stream|application/gltf-buffer|image/(png|jpeg|webp));base64,',value):raise ValueError('Unsupported embedded resource.')
            return
        decoded=unquote(value);safe_name(decoded)
        if decoded.casefold() not in names:raise ValueError('Missing local sidecar: '+decoded)
    if extension in ['glb','gltf']:
        if extension=='glb':
            if len(content)<20 or content[:4]!=b'glTF' or struct.unpack_from('<I',content,4)[0]!=2 or struct.unpack_from('<I',content,8)[0]!=len(content):raise ValueError('Invalid GLB header.')
            length,kind=struct.unpack_from('<II',content,12)
            if kind!=0x4e4f534a or length>len(content)-20:raise ValueError('Invalid GLB JSON chunk.')
            document=json.loads(content[20:20+length])
        else:document=json.loads(content)
        if not isinstance(document,dict):raise ValueError('GLTF document must be an object.')
        primitives=[primitive for mesh in document.get('meshes',[]) for primitive in mesh.get('primitives',[])]
        if any(any(key.startswith('TEXCOORD_') and key!='TEXCOORD_0' for key in primitive.get('attributes',{})) for primitive in primitives):raise ValueError('Multiple UV sets are not supported; preserve the source and prepare a single-UV texture mesh in Blender.')
        if 'KHR_texture_transform' in document.get('extensionsUsed',[]):raise ValueError('Bake material texture transforms before import; the engine cannot preserve them yet.')
        if document.get('skins') or document.get('animations') or any(primitive.get('targets') for primitive in primitives):raise ValueError('Only static meshes; skins, animation and morphs are not supported.')
        if document.get('extensionsRequired'):raise ValueError('Decode glTF extensions before static import.')
        for material in document.get('materials',[]):
            for field,factor in [('normalTexture','scale'),('occlusionTexture','strength')]:
                info=material.get(field,{})
                if info.get(factor,1)!=1:raise ValueError('Unsupported material factor '+field+'.'+factor+'; bake its effect in Blender before import/texturing/export.')
        for entry in document.get('buffers',[])+document.get('images',[]):
            if 'uri' in entry:uri(entry['uri'])
    if extension=='obj':
        for line in content.decode('utf-8-sig',errors='strict').splitlines():
            parts=line.split('#',1)[0].strip().split(maxsplit=1)
            if parts and parts[0].lower()=='mtllib':
                if len(parts)!=2:raise ValueError('Missing local MTL filename.')
                uri(parts[1])
    for key,body in sidecars.items():
        safe_name(key)
        if key.rsplit('.',1)[-1].lower() not in ['bin','mtl','png','jpg','jpeg','webp']:raise ValueError('Unsupported sidecar type.')
        if key.lower().endswith('.mtl'):
            for line in body.decode('utf-8-sig',errors='strict').splitlines():
                parts=line.split('#',1)[0].strip().split(maxsplit=1)
                if parts and (parts[0].lower().startswith('map_') or parts[0].lower() in ['bump','disp','decal']):
                    if len(parts)<2 or parts[1].startswith('-'):raise ValueError('Export MTL texture paths without options.')
                    uri(parts[1])
    return extension
