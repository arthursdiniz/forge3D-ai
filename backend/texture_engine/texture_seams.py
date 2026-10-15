"""Surface-adjacent UV seam diagnostics and strictly masked conservative repair."""
import numpy as np
from .texture_fusion import srgb_to_linear,linear_to_srgb

def seam_pairs(mesh,shape):
    from collections import defaultdict
    height,width=shape[:2];uv=np.asarray(mesh.visual.uv);span=max(np.ptp(mesh.vertices,axis=0).max(),1e-8);groups=defaultdict(list)
    for index,key in enumerate(np.rint(mesh.vertices/(span*1e-6)).astype('i8')):groups[tuple(key)].append(index)
    pairs=[]
    for group in groups.values():
        unique={tuple(np.rint(uv[index]*1e6).astype('i8')):index for index in group};values=list(unique.values())
        for index in values[1:]:
            first=values[0];normal_a=mesh.vertex_normals[first];normal_b=mesh.vertex_normals[index]
            if np.dot(normal_a,normal_b)<.98:continue
            coordinates=np.rint(uv[[first,index]]*np.array([width-1,height-1])).astype(int);coordinates[:,1]=height-1-coordinates[:,1]
            if coordinates.min()<0 or np.any(coordinates[:,0]>=width) or np.any(coordinates[:,1]>=height):continue
            pairs.append(tuple((int(y),int(x)) for x,y in coordinates))
    return pairs

def inspect_seams(mesh,image):
    pairs=seam_pairs(mesh,image.shape);errors=[float(np.abs(image[a][:3].astype(float)-image[b][:3]).mean()/255) for a,b in pairs]
    return {'sample_pairs':len(pairs),'mean_rgb_difference':round(float(np.mean(errors)),6) if errors else None,'max_rgb_difference':round(max(errors),6) if errors else None,'scope':'Duplicated world-position vertices across UV seams with compatible normals; not every seam sample or semantic error.'}

def correct_seams(mesh,image,editable):
    from scipy.ndimage import maximum_filter,minimum_filter
    output=image.copy();rgb=image[...,:3].astype(float)
    local=maximum_filter(rgb,size=(3,3,1))-minimum_filter(rgb,size=(3,3,1))
    for a,b in seam_pairs(mesh,image.shape):
        if not editable[a] or not editable[b] or image[a][3]!=image[b][3]:continue
        if max(local[a].max(),local[b].max())>8 or np.abs(rgb[a]-rgb[b]).max()>8:continue
        color=np.rint(linear_to_srgb(srgb_to_linear(np.array([rgb[a],rgb[b]])/255).mean(axis=0))*255).clip(0,255).astype('u1')
        output[a][:3]=color;output[b][:3]=color
    return output

def uv_density(mesh,mask,world_vertices=None):
    vertices=np.asarray(world_vertices if world_vertices is not None else mesh.vertices);triangles=vertices[mesh.faces];surface=np.linalg.norm(np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0]),axis=1)/2
    uv=np.asarray(mesh.visual.uv)[mesh.faces];delta=uv[:,1:]-uv[:,:1];area=np.abs(delta[:,0,0]*delta[:,1,1]-delta[:,0,1]*delta[:,1,0])/2
    height,width=mask.shape;center=uv.mean(axis=1);x=np.clip((center[:,0]*width).astype(int),0,width-1);y=np.clip(((1-center[:,1])*height).astype(int),0,height-1);selected=mask[y,x]&(surface>1e-12)&(area>1e-12)
    density=np.sqrt(area[selected]*width*height/surface[selected])
    return {'editable_texels':int(mask.sum()),'sampled_triangles':int(selected.sum()),'median_texels_per_world_unit':round(float(np.median(density)),3) if len(density) else None,'min_texels_per_world_unit':round(float(density.min()),3) if len(density) else None,'uv_changed':False,'scope':'Triangle-centroid region estimate using UV/world area; not semantic face segmentation or adaptive rebake.'}
