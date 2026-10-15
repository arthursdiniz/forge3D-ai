"""Actual image/mesh analysis and reviewable guides for bounded reconstruction."""
import hashlib,json
from pathlib import Path
import numpy as np
from PIL import Image
from .inference import infer_semantic,infer_depth
from .understanding import analyze_hair,head_component,depth_ordering
from .scalp import estimate_scalp
from .metrics import silhouette_metrics

def expand_head(box):
    l,t,r,b=box;fw=r-l;fh=b-t
    return [max(0,l-fw),max(0,t-fh*1.1),min(1,r+fw),min(1,b+fh*.35)]

def target_hair_box(source_mask,source_face,target_face):
    box=expand_head(target_face)
    if np.where(source_mask)[0].max(initial=0)/source_mask.shape[0]<source_face[3]:box[3]=target_face[3]
    return box

def map_reference(mask,source_face,target_face,size):
    import cv2
    h,w=mask.shape;l,t,r,b=target_face;sl,st,sr,sb=source_face;rows,cols=np.indices((size,size));x=sl+((cols+.5)/size-l)/(r-l)*(sr-sl);y=st+((rows+.5)/size-t)/(b-t)*(sb-st)
    return cv2.remap(mask.astype('u1'),(x*w-.5).astype('f4'),(y*h-.5).astype('f4'),cv2.INTER_NEAREST,borderMode=cv2.BORDER_CONSTANT)>0

def analyze_scene(scene,image,root,options,directory,source_sha=''):
    from backend.texture_engine.region_camera import RegionCamera
    from backend.texture_engine.face_detection import detect_anime
    from backend.texture_engine.region_masks import polygon_mask
    from .volume import scalp_guide
    from .scalp import scalp_sdf
    from backend.texture_engine.identity import world_triangles
    from backend.character_quality import canonical_vertices
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True);image=image.convert('RGBA');image.save(directory/'source.png')
    camera=RegionCamera(scene,options.get('front_axis','negative_y'),1024);model_image=Image.fromarray(camera.image);model_image.save(directory/'model_front.png')
    detections={};boxes={}
    for name,current in [('source',image),('target',model_image)]:
        boxes[name]=options.get(name+'_face')
        if not boxes[name] and options.get('style','anime') in ['anime','stylized']:
            detections[name]=detect_anime(current,root)
            if len(detections[name]['faces'])==1:boxes[name]=detections[name]['faces'][0]['box']
    if not boxes['source'] or not boxes['target']:
        report={'status':'manual_required','source_sha256':source_sha,'front_axis':options.get('front_axis','negative_y'),'source_size':list(image.size),'source_face':boxes['source'],'target_face':boxes['target'],'reason':'Select source and target face/head regions; no safe unique detected head.','detections':detections,'neural_ground_truth_accuracy':None}
        (directory/'hair_analysis.json').write_text(json.dumps(report,indent=2));return report
    head_box=options.get('head_box') or expand_head(boxes['source']);source_semantic=infer_semantic(image,head_box,root);target_semantic=infer_semantic(model_image,expand_head(boxes['target']),root)
    if source_semantic.get('mask') is None or target_semantic.get('mask') is None:raise ValueError('Hair semantic resources unavailable; original preserved.')
    source_mask=head_component(source_semantic['mask'],head_box);manual=options.get('hair_polygon')
    rows,cols=np.indices(source_mask.shape);xy=np.column_stack([(cols.ravel()+.5)/image.width,(rows.ravel()+.5)/image.height])
    if manual:source_mask=polygon_mask(xy,manual).reshape(source_mask.shape)&(np.asarray(image)[...,3]>128)
    manual_protected=np.zeros(source_mask.shape,bool)
    for protected in options.get('protected_polygons',[]):manual_protected|=polygon_mask(xy,protected).reshape(source_mask.shape)
    source_mask&=~manual_protected
    Image.fromarray(map_reference(manual_protected,boxes['source'],boxes['target'],camera.size).astype('u1')*255).save(directory/'manual_protected_mask.png')
    target_box=target_hair_box(source_mask,boxes['source'],boxes['target'])
    target_semantic['mask']=head_component(target_semantic['mask'],target_box)
    depth=infer_depth(image,head_box,root);depth_map=depth.pop('depth',None)
    for name,mask in [('hair_source_mask',source_mask),('hair_model_mask',target_semantic['mask'])]:Image.fromarray(mask.astype('u1')*255).save(directory/(name+'.png'))
    Image.fromarray(target_semantic['classes']).save(directory/'model_classes.png');Image.fromarray(source_semantic['classes']).save(directory/'source_classes.png')
    overlay=np.asarray(image).copy();overlay[source_mask,:3]=np.rint(overlay[source_mask,:3]*.45+np.array([60,230,160])*.55).astype('u1');Image.fromarray(overlay).save(directory/'mask_overlay.png')
    if depth_map is not None:
        np.save(directory/'relative_depth.npy',depth_map);valid=depth_map>0;low,high=np.percentile(depth_map[valid],[2,98]);visual=np.zeros_like(depth_map,dtype='u1');visual[valid]=np.clip((depth_map[valid]-low)/max(high-low,1e-6)*255,0,255).astype('u1');Image.fromarray(visual).save(directory/'depth.png')
    scalp=estimate_scalp(scene,camera,boxes['target']);understanding=analyze_hair(source_mask,boxes['source'],np.asarray(image),depth_map,options.get('preset','auto'));ordering=depth_ordering(depth_map,source_mask,boxes['source'])
    if understanding['status']=='reviewable':understanding['layers'].update(ordering)
    if understanding['status']!='reviewable' or scalp['status']!='reviewable':status='manual_required'
    else:
        status='reviewable';center=np.asarray(scalp['center']);radii=np.asarray(scalp['radii']);scale=camera.frame['scale'];sl,st,sr,sb=boxes['source'];tl,tt,tr,tb=boxes['target'];frame_center=np.asarray(camera.frame['center'])
        points=canonical_vertices(world_triangles(scene).reshape(-1,3),camera.axis);normalized=(points-center)/radii;radius=np.linalg.norm(normalized,axis=1);selected=(radius>.55)&(radius<2)&(normalized[:,1]>-.3)
        field=np.column_stack([normalized[selected]/radius[selected,None],radius[selected]]);field=field[::max(1,int(np.ceil(len(field)/4096)))];np.save(directory/'existing_head_field.npy',field)
        visible=camera.buffers[0][target_semantic['mask']&(camera.buffers[0][...,3]>.5),:3];distances=scalp_sdf(visible,scalp)
        understanding['existing_volume']={'visible_samples':len(visible),'scalp_distance_p10_p50_p90':np.percentile(distances,[10,50,90]).tolist() if len(visible) else None,'flattened_heuristic':bool(len(visible) and np.median(distances)<radii.min()*.08),'scope':'Distance to estimated scalp, not anatomical ground truth; original hair retained; adaptive base follows measured head envelope.'}
        understanding['existing_head_field']='existing_head_field.npy'
        for tip in understanding['tips']:
            u,v=tip['tip'];target=np.array([tl+(u-sl)/(sr-sl)*(tr-tl),tt+(v-st)/(sb-st)*(tb-tt)])
            point=np.array([frame_center[0]+(target[0]-.5)/scale,frame_center[1]+(.5-target[1])/scale,center[2]+radii[2]*.65])
            direction=(point[:2]-center[:2])/radii[:2];direction/=max(np.linalg.norm(direction),1e-6);root_direction=np.array([direction[0]*.65,direction[1]*.65,np.sqrt(1-.65**2)])
            if tip['zone']=='fringe':
                root_direction=np.array([np.clip(direction[0]*.45,-.5,.5),.65,.65]);root_direction/=np.linalg.norm(root_direction)
            px,py=np.clip(np.rint(target*camera.size).astype(int),0,camera.size-1);sample=camera.buffers[0][py,px]
            point[2]=max(point[2],float(sample[2])+radii[2]*.055 if sample[3]>.5 else point[2]);point[2]+=radii[2]*ordering['front_offset_fraction']
            tip['root_world']=(center+radii*root_direction).tolist();tip['tip_world']=point.tolist();tip['observation']='front contour + bounded relative layer ordering + existing visible mesh depth';tip['relative_depth_offset_fraction']=ordering['front_offset_fraction'];tip['already_covered']=bool(target_semantic['mask'][py,px] and sample[3]>.5)
        guide=scalp_guide(scalp)
        if options.get('front_axis')=='x':
            from backend.character_quality import view_vertices
            guide.vertices=view_vertices(guide.vertices,'right')
        guide.export(directory/'scalp.glb',include_normals=True)
    projected=map_reference(source_mask,boxes['source'],boxes['target'],camera.size);Image.fromarray(projected.astype('u1')*255).save(directory/'reference_aligned_mask.png')
    extra_records=[]
    if status=='reviewable':
        from .extra_views import extra_views
        extra_tips,extra_records=extra_views(scene,scalp,root,options,directory);understanding['tips'].extend(extra_tips)
    report={'status':status,'source_sha256':source_sha,'reference_pixel_sha256':hashlib.sha256(image.tobytes()).hexdigest(),'front_axis':options.get('front_axis','negative_y'),'source_size':list(image.size),'source_face':boxes['source'],'target_face':boxes['target'],'head_box':head_box,'target_head_box':expand_head(boxes['target']),'scalp':scalp,'understanding':understanding,'before_silhouette':silhouette_metrics(target_semantic['mask'],projected),'mask_source':'manual polygon' if manual else 'actual learned seven-class UNet; reviewable','semantic_resources':{name:value['resources'] for name,value in [('source',source_semantic),('target',target_semantic)]},'semantic_mean_response':source_semantic.get('hair_mean_response'),'depth':depth,'camera_frame':camera.frame,'options':options,'detections':detections,'ground_truth_mask_iou':None,'observed_views':['front'],'back_confidence':'low','extra_view_policy':'Uncalibrated additional views are not silently treated as ground truth.'}
    report['extra_views']=extra_records;report['observed_views']+= [v['view'] for v in extra_records if v['used_for_geometry']]
    if status=='manual_required':report['reason']=understanding.get('reason') or scalp.get('reason') or 'Review the hair mask and head/scalp regions before reconstruction.'
    if 'back' in report['observed_views']:report['back_confidence']='Observed real contour with manual scalp registration; hidden thickness still inferred.'
    (directory/'hair_analysis.json').write_text(json.dumps(report,indent=2),encoding='utf-8');return report
