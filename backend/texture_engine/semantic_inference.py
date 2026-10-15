"""Actual pinned portrait parser reuse; image/code/crop bound offline cache."""
import hashlib,json,time
from pathlib import Path
import numpy as np
from PIL import Image
from .semantic_masks import map_native,save_masks,region_features
from .semantic_taxonomy import SUPPORTED

def segment_image(image,root,crop,profile,directory):
    from backend.hair.resources import verify_resources
    root=Path(root);directory=Path(directory);directory.mkdir(parents=True,exist_ok=True);started=time.perf_counter();image=image.convert('RGBA');rgba=np.asarray(image);labels=np.zeros(rgba.shape[:2],'u1');labels[rgba[...,3]<=128]=1;native=None;resources=verify_resources(root);reason=None
    crop=list(crop) if crop else None
    if profile!='manual' and resources['ready'] and crop is None:
        from .face_detection import detect_anime
        from backend.hair.analysis import expand_head
        detected=detect_anime(image,root)
        if len(detected['faces'])==1:crop=expand_head(detected['faces'][0]['box'])
        else:reason='No unique anime head; mark a portrait crop or use manual masks.'
    key_data={'pixels':hashlib.sha256(rgba.tobytes()).hexdigest(),'size':list(image.size),'crop':crop,'profile':profile,'code':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'manifest':resources.get('manifest')}
    key=hashlib.sha256(json.dumps(key_data,sort_keys=True).encode()).hexdigest();cache=root/'cache/semantic'/key;cached=False;measurement=None;executed=False
    if profile!='manual' and resources['ready'] and crop:
        if (cache/'native.npy').is_file() and (cache/'report.json').is_file():
            value=np.load(cache/'native.npy',allow_pickle=False)
            if value.shape==labels.shape and value.dtype==np.uint8:native=value;measurement=json.loads((cache/'report.json').read_text());cached=True
        if native is None:
            from backend.hair.inference import infer_semantic
            response=infer_semantic(image,crop,root)
            if response.get('classes') is not None:
                native=response['classes'];measurement=response['resources'];executed=True;cache.mkdir(parents=True,exist_ok=True);np.save(cache/'native.npy',native,allow_pickle=False);(cache/'report.json').write_text(json.dumps(measurement))
            else:reason=response.get('reason','Portrait parser unavailable.')
        if native is not None:labels=map_native(native,crop,rgba[...,3])
    elif profile!='manual' and not resources['ready']:reason='Verified local portrait weights are unavailable; manual masks required.'
    origin=np.where(labels>0,1,0).astype('u1');save_masks(directory,image,labels,origin,native)
    report={'status':'reviewable' if native is not None else 'manual_required','reason':reason,'provider':'Anime-Face-Segmentation UNet/MobileNet' if native is not None else 'manual','supported_classes':SUPPORTED if native is not None else [],'unsupported_classes':'Broader taxonomy requires explicit manual labels; clothes is not shirt/shorts.','portrait_crop':crop,'source_pixel_sha256':key_data['pixels'],'source_size':list(image.size),'cache_key':key,'cache_reused':cached,'neural_executed':executed,'cached_neural_result':cached,'neural_resources':measurement,'seconds':round(time.perf_counter()-started,4),'confidence':None,'confidence_scope':'Categorical classes; no calibrated semantic accuracy or artistic fidelity score.','features':region_features(rgba,labels),'resources':resources.get('manifest'),'scope':'Portrait parser only; outside crop unknown. Alpha background is observed; stylized/realistic extrapolation not validated.'}
    (directory/'segmentation.json').write_text(json.dumps(report,indent=2),encoding='utf-8');return labels,origin,report
