import hashlib,json,time
from pathlib import Path
import numpy as np
from PIL import Image
from .semantic_inference import segment_image
from .semantic_masks import apply_strokes,apply_polygons,save_masks,region_features
from .semantic_atlas import YAW,write_analysis_atlas
from .region_camera import RegionCamera

def analyze_semantics(scene,root,settings,directory,source_sha):
    directory=Path(directory);started=time.perf_counter();views={};needs_review=[]
    for name,options in settings['views'].items():
        folder=directory/'views'/name;folder.mkdir(parents=True,exist_ok=True);source=Image.open(folder/'source.png').convert('RGBA');camera=RegionCamera(scene,settings['front_axis'],512,yaw=YAW[name]);target=Image.fromarray(camera.image);target.save(folder/'target.png');records={}
        for role,image in [('source',source),('target',target)]:
            labels,origin,record=segment_image(image,root,options.get(role+'_crop'),options.get('profile','anime'),folder/(role+'_learned'));effective,origin=apply_polygons(labels,origin,options.get(role+'_polygons',[]));effective,origin=apply_strokes(labels,options.get(role+'_strokes',[]),effective,origin);Image.fromarray(effective).save(folder/(role+'_labels.png'));Image.fromarray(origin).save(folder/(role+'_origin.png'));save_masks(folder/(role+'_effective'),image,effective,origin);record['features']=region_features(np.asarray(image),effective);record['manual_strokes']=len(options.get(role+'_strokes',[]));record['manual_polygons']=len(options.get(role+'_polygons',[]));record['known_pixels']=int((effective>1).sum());records[role]=record
        registration=options['registration']
        if records['source']['known_pixels']<32 or (records['target']['known_pixels']<32 and not registration.get('accept_unknown_target')):needs_review.append(name)
        views[name]={'camera_frame':camera.frame,'registration':registration,'source':records['source'],'target':records['target'],'source_pixel_sha256':hashlib.sha256(np.asarray(source).tobytes()).hexdigest(),'target_pixel_sha256':hashlib.sha256(camera.image.tobytes()).hexdigest(),'source_size':list(source.size),'scope':'Real image + actual mesh view, reviewed mapping required; no automatic pose correspondence.'}
        views[name]['file_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.glob('*.png')}
    report={'status':'manual_required' if needs_review else 'reviewable','reason':'Review/paint source and target masks in: '+', '.join(needs_review) if needs_review else None,'front_axis':settings['front_axis'],'source_sha256':source_sha,'views':views,'options':settings,'atlas':[],'confidence':None,'pose_context':'Pose landmarks can be suggestions; not semantic classes.','seconds':None}
    context={**report,'directory':str(directory)}
    context_path=directory/'character_context.json'
    if context_path.is_file():report['character_context']=json.loads(context_path.read_text(encoding='utf-8'))
    try:report['atlas']=write_analysis_atlas(scene,context,directory)
    except ValueError as error:report['atlas_reason']=str(error);report['reason']=str(error);report['status']='manual_required'
    shared=[r['geometry'] for r in report['atlas'] if r['class_texels'].get('4',0)>0 and (r['class_texels'].get('3',0)>0 or r['class_texels'].get('2',0)>0)]
    report['hair_geometry_hint']={'hair_and_face_share_primitives':shared,'scope':'Semantic estimates on the same original primitive; not proof of flatness or absent volume. Texture cannot create volume. Inspect the separate Cabelo3D module if shape is deficient.'}
    report['seconds']=round(time.perf_counter()-started,3);(directory/'semantic_analysis.json').write_text(json.dumps(report,indent=2),encoding='utf-8');return report
