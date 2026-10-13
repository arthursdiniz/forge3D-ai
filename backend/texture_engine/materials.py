import copy
import numpy as np

def unity_metallic_smoothness(packed,metallic_factor=1.,roughness_factor=1.):
    values=np.asarray(packed,dtype=float)/255.
    output=np.zeros((*values.shape[:2],4),dtype=np.uint8)
    output[...,0]=np.rint(np.clip(values[...,2]*metallic_factor,0,1)*255)
    output[...,3]=np.rint((1-np.clip(values[...,1]*roughness_factor,0,1))*255)
    return output

def build_material(previous,image,name,overrides):
    import trimesh
    if isinstance(previous,trimesh.visual.material.PBRMaterial):material=copy.deepcopy(previous)
    elif previous is not None:material=previous.to_pbr()
    else:material=trimesh.visual.material.PBRMaterial(metallicFactor=0,roughnessFactor=.65)
    alpha=int(material.baseColorFactor[3]) if material.baseColorFactor is not None else 255
    material.name=name;material.baseColorTexture=image;material.baseColorFactor=[255,255,255,alpha]
    if overrides.get('metallic') is not None:material.metallicFactor=overrides['metallic']
    if overrides.get('roughness') is not None:material.roughnessFactor=overrides['roughness']
    return material
