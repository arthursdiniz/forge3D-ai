"""Small sequential neural stages; explicit local weights, no implicit downloads."""
import gc,hashlib,importlib.util,sys,time
from pathlib import Path
import numpy as np
from PIL import Image
from .resources import verify_resources
CLASS_NAMES=['background','hair','eyes','mouth','face','skin','clothes']

def square_crop(image,box):
    w,h=image.size;l,t,r,b=box
    if not all(np.isfinite(v) and 0<=v<=1 for v in box) or l>=r or t>=b:raise ValueError('Invalid head rectangle.')
    side=max(2,int(np.ceil(max((r-l)*w,(b-t)*h))));x=int(round((l+r)*w/2-side/2));y=int(round((t+b)*h/2-side/2))
    return image.convert('RGBA').crop((x,y,x+side,y+side)),{'pixel_box':[x,y,x+side,y+side],'original_size':[w,h]}

def restore_prediction(prediction,frame,size,nearest=False):
    import cv2
    x0,y0,x1,y1=frame['pixel_box'];w,h=size
    expanded=cv2.resize(np.asarray(prediction),(x1-x0,y1-y0),interpolation=cv2.INTER_NEAREST if nearest else cv2.INTER_LINEAR)
    output=np.zeros((h,w),expanded.dtype);l,t,r,b=max(0,x0),max(0,y0),min(w,x1),min(h,y1)
    if l<r and t<b:output[t:b,l:r]=expanded[t-y0:b-y0,l-x0:r-x0]
    return output

def _rgb(crop):
    canvas=Image.new('RGB',crop.size,'white');canvas.paste(crop.convert('RGB'),mask=crop.getchannel('A'));return np.asarray(canvas)

def _resources(root):
    ready=verify_resources(root)
    if not ready['ready']:return None,{'status':'manual_required','mask':None,'neural_validated':False,'reason':ready.get('reason','Missing resources.')}
    return ready['manifest'],None

def _measure(torch,started,device):
    import os,psutil
    if device=='cuda':torch.cuda.synchronize()
    memory=psutil.Process(os.getpid()).memory_info()
    return {'seconds':round(time.perf_counter()-started,3),'device':device,'peak_allocated_mib':round(torch.cuda.max_memory_allocated()/1024**2,2) if device=='cuda' else 0,'peak_reserved_mib':round(torch.cuda.max_memory_reserved()/1024**2,2) if device=='cuda' else 0,'process_peak_working_set_mib':round(getattr(memory,'peak_wset',memory.rss)/1024**2,2),'offline':True}

def depth_tensor(rgb,root,torch,device):
    import cv2
    sys.path.insert(0,str(Path(root)/'vendor/Depth-Anything-V2'))
    from depth_anything_v2.util.transform import Resize,NormalizeImage,PrepareForNet
    value={'image':np.asarray(rgb,dtype='f4')/255}
    for transform in [Resize(518,518,resize_target=False,keep_aspect_ratio=True,ensure_multiple_of=14,resize_method='lower_bound',image_interpolation_method=cv2.INTER_CUBIC),NormalizeImage(mean=[.485,.456,.406],std=[.229,.224,.225]),PrepareForNet()]:value=transform(value)
    return torch.from_numpy(value['image']).unsqueeze(0).to(device)

def infer_semantic(image,head_box,root,device='cuda'):
    root=Path(root);manifest,fallback=_resources(root)
    if fallback:return fallback
    import torch
    device='cuda' if device=='cuda' and torch.cuda.is_available() else 'cpu';started=time.perf_counter()
    if device=='cuda':torch.cuda.reset_peak_memory_stats()
    model=tensor=None
    try:
        path=root/'vendor/anime-hair-segmentation/network.py';spec=importlib.util.spec_from_file_location('forge_hair_unet',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        model=module.UNet();model.load_state_dict(torch.load(root/'models/hair/anime-unet.pth',map_location='cpu',weights_only=True));model=model.to(device).eval()
        crop,frame=square_crop(image,head_box);rgb=_rgb(crop);rgb=np.asarray(Image.fromarray(rgb).resize((512,512),Image.Resampling.BILINEAR))
        tensor=torch.from_numpy(rgb.copy()).permute(2,0,1).float().div(255).unsqueeze(0).to(device)
        with torch.inference_mode():probability=model(tensor)[0].float().cpu().numpy()
        labels=restore_prediction(np.argmax(probability,axis=0).astype('u1'),frame,image.size,True);hair=restore_prediction(probability[1],frame,image.size)
        alpha=np.asarray(image.convert('RGBA'))[...,3]>128;mask=(labels==1)&alpha;face=np.isin(labels,[2,3,4,5])&alpha
        # These probabilities are uncalibrated model responses, not fidelity.
        return {'status':'reviewable' if mask.sum()>=32 else 'manual_required','mask':mask,'hair_probability':hair,'classes':labels,'face_mask':face,'frame':frame,'class_names':CLASS_NAMES,'hair_mean_response':round(float(hair[mask].mean()),4) if mask.any() else None,'response_scope':'Uncalibrated semantic response; review anime/accessories/skin boundaries.','neural_validated':True,'resources':_measure(torch,started,device)}
    finally:
        del model,tensor;gc.collect()
        if device=='cuda':torch.cuda.empty_cache()

def infer_depth(image,head_box,root,device='cuda'):
    root=Path(root);manifest,fallback=_resources(root)
    if fallback:return {'status':'unavailable','depth':None,'relative_only':True,'reason':fallback['reason']}
    import torch
    device='cuda' if device=='cuda' and torch.cuda.is_available() else 'cpu';started=time.perf_counter()
    if device=='cuda':torch.cuda.reset_peak_memory_stats()
    model=tensor=None
    try:
        vendor=root/'vendor/Depth-Anything-V2';sys.path.insert(0,str(vendor));from depth_anything_v2.dpt import DepthAnythingV2
        model=DepthAnythingV2(encoder='vits',features=64,out_channels=[48,96,192,384]);model.load_state_dict(torch.load(root/'models/hair/depth-small.pth',map_location='cpu',weights_only=True));model=model.to(device).eval()
        crop,frame=square_crop(image,head_box);rgb=_rgb(crop);tensor=depth_tensor(rgb,root,torch,device)
        with torch.inference_mode():predicted=model(tensor)[0].float().cpu().numpy()
        depth=restore_prediction(predicted,frame,image.size)
        return {'status':'auxiliary_relative','depth':depth,'frame':frame,'relative_only':True,'metric_thickness':False,'neural_validated':True,'scope':'Relative inverse-depth ordering can fail on anime; constrained by existing mesh and silhouette, never direct extrusion.','resources':_measure(torch,started,device)}
    finally:
        del model,tensor;gc.collect()
        if device=='cuda':torch.cuda.empty_cache()
