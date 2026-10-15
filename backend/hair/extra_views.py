"""Optional real side/back observations with explicit reviewed scalp registration."""
import numpy as np
from PIL import Image
from .inference import infer_semantic,infer_depth
from .understanding import head_component,analyze_hair,depth_ordering

def extra_views(scene,scalp,root,options,directory):
    from backend.texture_engine.region_camera import RegionCamera
    center=np.asarray(scalp['center']);radii=np.asarray(scalp['radii']);tips=[];records=[]
    for name,yaw in [('side',90),('back',180)]:
        path=directory/f'reference_{name}.png'
        if not path.is_file():continue
        box=options.get('extra_scalp_boxes',{}).get(name)
        if not box:records.append({'view':name,'status':'manual_registration_required','used_for_geometry':False});continue
        image=Image.open(path).convert('RGBA');l,t,r,b=box;fw=r-l;fh=b-t;crop=[max(0,l-fw*.6),max(0,t-fh*.6),min(1,r+fw*.6),min(1,b+fh*.8)]
        semantic=infer_semantic(image,crop,root);mask=head_component(semantic['mask'],crop);Image.fromarray(mask.astype('u1')*255).save(directory/f'hair_{name}_mask.png')
        depth=infer_depth(image,crop,root);ordering=depth_ordering(depth.pop('depth',None),mask,box);context=analyze_hair(mask,box,np.asarray(image),preset=options.get('preset','auto'))
        if context['status']!='reviewable':records.append({'view':name,'status':'insufficient_hair_mask','used_for_geometry':False});continue
        camera=RegionCamera(scene,options.get('front_axis','negative_y'),1024,yaw=yaw);angle=np.deg2rad(yaw);rotation=np.array([[np.cos(angle),0,np.sin(angle)],[0,1,0],[-np.sin(angle),0,np.cos(angle)]]);c=center@rotation;rx=radii[2] if name=='side' else radii[0];rz=radii[0] if name=='side' else radii[2]
        Image.fromarray(camera.image).save(directory/f'model_{name}.png')
        for guide in context['tips'][:16]:
            u,v=guide['tip'];point=np.array([c[0]+(u-(l+r)/2)/(fw/2)*rx,c[1]+((t+b)/2-v)/(fh/2)*radii[1],c[2]+rz*.75]);xy=camera.coordinates((point@rotation.T)[None,:]);px,py=np.clip(np.rint(xy[0]*camera.size).astype(int),0,camera.size-1);sample=camera.buffers[0][py,px]
            if sample[3]>.5:point[2]=max(point[2],float(sample[2])+rz*.055)
            point[2]+=rz*ordering['front_offset_fraction']
            direction=point-c;direction/=max(np.linalg.norm(direction),1e-9);guide.update(root_world=((c+np.array([rx,radii[1],rz])*direction*.95)@rotation.T).tolist(),tip_world=(point@rotation.T).tolist(),zone=name,observation=f'real {name} reference with manually reviewed scalp box; hidden local depth constrained by existing mesh')
            tips.append(guide)
        records.append({'view':name,'status':'reviewable_manual_alignment','used_for_geometry':True,'source_scalp_box':box,'semantic_resources':semantic['resources'],'depth':depth,'layer_ordering':ordering,'guides':len(context['tips'][:16]),'scope':'Real observed contour; scalp registration and hidden thickness remain estimates.'})
    return tips,records
