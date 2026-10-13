"""Extract actual glTF maps/factors for independently configured Unity slots."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))

def export_materials(scene,directory):
    import numpy as np
    from PIL import Image
    from backend.texture_engine.materials import unity_metallic_smoothness
    records=[];seen={};directory=Path(directory)
    for mesh in scene.geometry.values():
        material=getattr(mesh.visual,'material',None)
        if material is None:continue
        if not hasattr(material,'baseColorTexture'):material=material.to_pbr()
        name=material.name or 'Material'
        if name in seen:
            if material==seen[name]:continue
            raise ValueError('Distinct material appearances share a name; rename source materials before export.')
        seen[name]=material;index=len(records);folder=directory/'Textures'/f'{index:03d}';folder.mkdir(parents=True,exist_ok=True)
        record={'name':name,'color':(np.asarray(material.baseColorFactor,dtype=float)/255).tolist() if material.baseColorFactor is not None else [1,1,1,1],'metallic':material.metallicFactor if material.metallicFactor is not None else 1.,'roughness':material.roughnessFactor if material.roughnessFactor is not None else 1.,'alpha_mode':material.alphaMode or 'OPAQUE','alpha_cutoff':material.alphaCutoff if material.alphaCutoff is not None else .5,'double_sided':material.doubleSided,'emissive_factor':material.emissiveFactor.tolist() if material.emissiveFactor is not None else [0,0,0]}
        for attribute,label in [('baseColorTexture','albedo'),('normalTexture','normal'),('occlusionTexture','occlusion'),('metallicRoughnessTexture','metallic_roughness'),('emissiveTexture','emissive')]:
            value=getattr(material,attribute,None)
            if value is not None:value.save(folder/(label+'.png'));record[label]=f'Textures/{index:03d}/{label}.png'
        if material.metallicRoughnessTexture is not None:
            pixels=unity_metallic_smoothness(material.metallicRoughnessTexture,record['metallic'],record['roughness'])
            Image.fromarray(pixels).save(folder/'UnityMetallicSmoothness.png');record['metallic_smoothness']=f'Textures/{index:03d}/UnityMetallicSmoothness.png'
        if material.occlusionTexture is not None:
            ao=np.asarray(material.occlusionTexture.convert('RGB'))[...,0]
            Image.fromarray(np.repeat(ao[...,None],3,axis=-1)).save(folder/'UnityOcclusion.png');record['unity_occlusion']=f'Textures/{index:03d}/UnityOcclusion.png'
        records.append(record)
    (directory/'materials.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
    return records

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--input',required=True);parser.add_argument('--output',required=True);args=parser.parse_args()
    import trimesh
    from backend.texture_engine.import_safety import validate_resources
    validate_resources('model.glb',Path(args.input).read_bytes(),{})
    export_materials(trimesh.load(args.input,force='scene',process=False),Path(args.output))
if __name__=='__main__':main()
