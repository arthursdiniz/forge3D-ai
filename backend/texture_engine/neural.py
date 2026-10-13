"""Official MV-Adapter neural inference with native Windows control/fusion adapters.

Vendor weights and joint attention are unchanged. CPU offload addresses the 8GB
budget. No CV-CUDA, nvdiffrast, gated downloads, remote inference or fake filling.
"""
import gc
import hashlib
import json
import os
import socket
import sys
import time
import types
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
STYLE_PROMPTS={'free':'','anime':'anime character texture, crisp eyes, clean clothing colors, cel shaded painted appearance','stylized':'stylized game asset, coherent color palette, clean painted details','realistic':'realistic surface appearance, detailed natural materials','hand_painted':'hand painted game texture, carefully painted surface details','low_poly':'low poly stylized game texture, clean simple color regions'}

def preserve_shared_caches(module):
    # Accelerate send_to_device normally reconstructs dictionaries, losing the
    # vendor's mutable reference cache. These tensors already execute on CUDA.
    for child in module.modules():
        hook=getattr(child,'_hf_hook',None)
        for item in getattr(hook,'hooks',[hook]):
            if item is not None and hasattr(item,'skip_keys'):
                item.skip_keys=list(set((item.skip_keys or [])+['cross_attention_kwargs','cache_hidden_states','ref_hidden_states']))

def verify_resources():
    manifests=[]
    for name in ['sdxl','adapter']:
        folder=ROOT/'models/texture'/name;manifest=json.loads((folder/'download_manifest.json').read_text(encoding='utf-8'))
        for record in manifest['files']:
            path=folder/record['path']
            if path.stat().st_size!=record['bytes']:raise RuntimeError('Texture weight size mismatch.')
            digest=hashlib.sha256()
            with path.open('rb') as stream:
                while chunk:=stream.read(8*1024*1024):digest.update(chunk)
            if digest.hexdigest()!=record['sha256']:raise RuntimeError('Texture weight SHA256 mismatch.')
        manifests.append({'repo':manifest['repo'],'revision':manifest['revision'],'license':manifest['license']})
    return manifests

def generate_views(scene,references,options,directory):
    os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_HUB_DISABLE_TELEMETRY='1')
    def blocked(*args,**kwargs):raise RuntimeError('Network disabled during texture inference.')
    socket.socket.connect=blocked;socket.create_connection=blocked
    import numpy as np
    import torch
    from PIL import Image
    from .native import NativeControls
    from accelerate import cpu_offload
    from diffusers import DDPMScheduler
    sys.path.insert(0,str(ROOT/'vendor/MV-Adapter'))
    # Unneeded utils package initialization eagerly imports nvdiffrast/CV-CUDA.
    # Namespace those packages; actual requested pure Python modules still load.
    for name,relative in [('mvadapter.utils','mvadapter/utils'),('mvadapter.utils.mesh_utils','mvadapter/utils/mesh_utils')]:
        module=types.ModuleType(name);module.__path__=[str(ROOT/'vendor/MV-Adapter'/relative)];sys.modules[name]=module
    from mvadapter.models.attention_processor import DecoupledMVRowColSelfAttnProcessor2_0
    from mvadapter.schedulers.scheduling_shift_snr import ShiftSNRScheduler
    image_mode=options['conditioning']=='image'
    if image_mode:
        from mvadapter.pipelines.pipeline_mvadapter_i2mv_sdxl import MVAdapterI2MVSDXLPipeline as Pipeline
        weight='mvadapter_ig2mv_sdxl.safetensors'
    else:
        from mvadapter.pipelines.pipeline_mvadapter_t2mv_sdxl import MVAdapterT2MVSDXLPipeline as Pipeline
        weight='mvadapter_tg2mv_sdxl.safetensors'
    if not torch.cuda.is_available():raise RuntimeError('CUDA unavailable for neural texturing.')
    free,total=torch.cuda.mem_get_info()
    if free<3*1024**3:raise RuntimeError('CUDA out of memory: at least 3 GB free required for sequential offload profile.')
    started=time.perf_counter();torch.cuda.reset_peak_memory_stats();pipe=None
    try:
        print(json.dumps({'stage':'MV-Adapter: verificando SHA-256 dos pesos locais'}),flush=True)
        manifests=verify_resources()
        controls=NativeControls(scene,options['front_axis'],512)
        folder=Path(directory)/'neural_views';folder.mkdir(parents=True,exist_ok=True)
        for index,view in enumerate(controls.views):
            Image.fromarray(np.rint(controls.controls[index,:3].transpose(1,2,0)*255).astype('u1')).save(folder/(view+'_position.png'))
            Image.fromarray(np.rint(controls.controls[index,3:].transpose(1,2,0)*255).astype('u1')).save(folder/(view+'_normal.png'))
        print(json.dumps({'stage':'MV-Adapter: carregando SDXL e adaptador com offload sequencial'}),flush=True)
        pipe=Pipeline.from_pretrained(str(ROOT/'models/texture/sdxl'),torch_dtype=torch.float16,variant='fp16',local_files_only=True,add_watermarker=False)
        pipe.scheduler=ShiftSNRScheduler.from_scheduler(pipe.scheduler,shift_mode='interpolated',shift_scale=8.,scheduler_class=DDPMScheduler)
        pipe.init_custom_adapter(num_views=6,self_attn_processor=DecoupledMVRowColSelfAttnProcessor2_0)
        pipe.load_custom_adapter(str(ROOT/'models/texture/adapter'),weight_name=weight,local_files_only=True)
        pipe.to(dtype=torch.float16);pipe.cond_encoder.to(dtype=torch.float16)
        # VAE changes dtype for fp32 encode/decode; keep it outside meta hooks.
        pipe._exclude_from_cpu_offload=['vae']
        pipe.enable_sequential_cpu_offload();cpu_offload(pipe.cond_encoder,execution_device=torch.device('cuda'))
        preserve_shared_caches(pipe.unet)
        pipe.enable_vae_slicing();pipe.enable_vae_tiling()
        seed=options['seed'] if options['seed'] is not None else int.from_bytes(os.urandom(4),'little')
        prompt=', '.join(part for part in [options['prompt'] or 'high quality coherent texture',STYLE_PROMPTS[options['style']]] if part)
        kwargs={}
        if image_mode:
            image=Image.fromarray(references['front']).convert('RGBA');alpha=np.asarray(image)[...,3];ys,xs=np.nonzero(alpha>0)
            if not len(xs):raise ValueError('Empty image reference.')
            image=image.crop((max(0,int(xs.min())-1),max(0,int(ys.min())-1),min(image.width,int(xs.max())+2),min(image.height,int(ys.max())+2)))
            image.thumbnail((460,460),Image.Resampling.LANCZOS)
            canvas=Image.new('RGBA',(512,512),(128,128,128,255));canvas.alpha_composite(image,((512-image.width)//2,(512-image.height)//2));reference=canvas.convert('RGB');reference.save(folder/'reference_conditioning.png')
            kwargs.update(reference_image=reference,reference_conditioning_scale=options['fidelity'])
        print(json.dumps({'stage':'MV-Adapter: inferência real de seis vistas conjuntas · 20 passos'}),flush=True)
        inference_start=time.perf_counter()
        with torch.inference_mode():
            images=pipe(prompt,height=512,width=512,num_inference_steps=20,guidance_scale=3. if image_mode else 7.,num_images_per_prompt=6,control_image=torch.from_numpy(controls.controls).to(device='cuda',dtype=torch.float16),control_conditioning_scale=1.,generator=torch.Generator(device='cuda').manual_seed(seed),negative_prompt='watermark, text artifacts, blurry, noisy, inconsistent clothing colors',**kwargs).images
        torch.cuda.synchronize();elapsed=time.perf_counter()-inference_start
        if len(images)!=6:raise RuntimeError('Neural pipeline did not produce six joint views.')
        outputs={}
        for view,image in zip(controls.views,images):
            rgb=np.asarray(image.convert('RGB'))
            if not np.isfinite(rgb).all() or rgb.std()<1:raise RuntimeError('Invalid or empty neural image output.')
            image.save(folder/(view+'.png'))
            outputs[view]=np.dstack([rgb,np.uint8(controls.rasters[view][...,3]>.5)*255])
        metadata={'model':'MV-Adapter SDXL','resources':manifests,'vendor_revision':'4277e0018232bac82bb2c103caf0893cedb711be','joint_views':6,'conditioning':options['conditioning'],'seed':seed,'prompt':prompt,'reference_scale':options['fidelity'] if image_mode else None,'steps':20,'native_resolution':512,'native_profile_limitation':'SDXL official texture example uses 768; this 512 profile prioritizes 8GB compatibility, atlas size cannot recover missing native detail.','offload':'sequential CPU submodule offload; VAE GPU outside dtype-changing meta hooks; control encoder CPU offload','vae_slicing':True,'vae_tiling':True,'dtype':'float16; VAE force_upcast float32','device':torch.cuda.get_device_name(),'total_vram_mb':round(total/1024**2,1),'peak_allocated_mb':round(torch.cuda.max_memory_allocated()/1024**2,1),'peak_reserved_mb':round(torch.cuda.max_memory_reserved()/1024**2,1),'inference_seconds':round(elapsed,2),'wall_seconds':round(time.perf_counter()-started,2),'offline':True,'generated_channels':['albedo'],'semantic_fidelity_verified':False}
        (Path(directory)/'neural.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
        return outputs,controls,metadata
    except Exception as error:
        (Path(directory)/'neural_failure.json').write_text(json.dumps({'error':str(error),'wall_seconds':round(time.perf_counter()-started,2),'peak_allocated_mb':round(torch.cuda.max_memory_allocated()/1024**2,1),'peak_reserved_mb':round(torch.cuda.max_memory_reserved()/1024**2,1),'offline':True},indent=2),encoding='utf-8')
        raise
    finally:
        if pipe is not None:del pipe
        gc.collect();torch.cuda.empty_cache()
