"""Real native multiview test, isolated and offline. No fake fallback."""
import argparse
import hashlib
import json
import os
import socket
import sys
import time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'vendor/Hunyuan3D-2'))
os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1')
def forbidden(*args,**kwargs):raise RuntimeError('Network blocked during local inference.')
socket.socket.connect=forbidden;socket.create_connection=forbidden
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--references',required=True);parser.add_argument('--output',required=True);parser.add_argument('--offload',action='store_true');parser.add_argument('--steps',type=int,default=50);parser.add_argument('--resolution',type=int,default=256);args=parser.parse_args()
    output=Path(args.output).resolve()
    if output.exists():raise RuntimeError('Preserve prior experiment.')
    output.mkdir(parents=True)
    import torch,numpy as np,psutil
    from PIL import Image
    from hy3dgen.shapegen import Hunyuan3DDiTFlowMatchingPipeline
    from backend.mesh_quality import inspect_mesh
    from safetensors.torch import save_file
    started=time.perf_counter();torch.cuda.reset_peak_memory_stats();weights=ROOT/'models/hunyuan-mv/hunyuan3d-dit-v2-mv'
    pipe=None
    try:
        pipe=Hunyuan3DDiTFlowMatchingPipeline.from_single_file(str(weights/'model.fp16.safetensors'),str(weights/'config.yaml'),device='cpu' if args.offload else 'cuda',dtype=torch.float16,use_safetensors=True)
        for model in [pipe.model,pipe.vae,pipe.conditioner]:model.eval()
        if args.offload:pipe.enable_model_cpu_offload(gpu_id=0)
        load_seconds=time.perf_counter()-started
        refs=Path(args.references);images={name:Image.open(refs/(name+'.png')).convert('RGBA') for name in ['front','left','back']}
        assert all(image.getchannel('A').getextrema()[0]<255 for image in images.values())
        def callback(index,timestep,values):
            print(json.dumps({'stage':f'Native multiview diffusion {index+1}/{args.steps}'}),flush=True)
            if index==args.steps-1:save_file({'latents':values.prev_sample.detach().cpu().contiguous()},str(output/'latents.safetensors'))
        with torch.inference_mode():
            mesh=pipe(image=images,num_inference_steps=args.steps,guidance_scale=5.0,generator=torch.Generator(device='cuda').manual_seed(42),octree_resolution=args.resolution,num_chunks=8000,mc_algo='mc',callback=callback,callback_steps=1)[0]
        if mesh is None or not len(mesh.faces) or not np.isfinite(mesh.vertices).all():raise RuntimeError('No valid multiview mesh.')
        mesh.export(output/'original.glb',include_normals=True);mesh.export(output/'raw_generation.glb',include_normals=True);torch.cuda.synchronize()
        report={'passed':True,'native_multiview':True,'views':list(images),'view_sha256':{name:hashlib.sha256((refs/(name+'.png')).read_bytes()).hexdigest() for name in images},'seed':42,'steps':args.steps,'guidance':5,'resolution':args.resolution,'offload':args.offload,'dtype':'float16','triangles':len(mesh.faces),'integrity':inspect_mesh(mesh.vertices,mesh.faces,normals=mesh.vertex_normals),'seconds':round(time.perf_counter()-started,2),'load_seconds':round(load_seconds,2),'peak_vram_mb':round(torch.cuda.max_memory_allocated()/1024**2,1),'peak_reserved_mb':round(torch.cuda.max_memory_reserved()/1024**2,1),'rss_mb':round(psutil.Process().memory_info().rss/1024**2,1),'offline_network_blocked':True}
        (output/'experiment.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report),flush=True)
    except Exception as error:
        report={'passed':False,'error':str(error),'type':type(error).__name__,'offload':args.offload,'seconds':round(time.perf_counter()-started,2),'peak_vram_mb':round(torch.cuda.max_memory_allocated()/1024**2,1),'peak_reserved_mb':round(torch.cuda.max_memory_reserved()/1024**2,1)}
        (output/'experiment.json').write_text(json.dumps(report,indent=2),encoding='utf-8');raise
    finally:
        del pipe
        import gc;gc.collect();torch.cuda.empty_cache()
if __name__=='__main__':
    from backend.instance import InstanceLock
    lock=InstanceLock(ROOT/'data/gpu.lock');lock.acquire()
    try:main()
    finally:lock.release()
