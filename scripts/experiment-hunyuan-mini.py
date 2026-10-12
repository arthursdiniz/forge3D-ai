"""User-authorized real shape experiment, kept separate from product availability."""
import argparse
import hashlib
import json
import os
import socket
import sys
import time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'vendor/Hunyuan3D-2'))
os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_HUB_DISABLE_TELEMETRY='1')
def no_network(*args,**kwargs):raise RuntimeError('Network blocked during local inference.')
socket.socket.connect=no_network;socket.create_connection=no_network

def stage(message):print(json.dumps({'stage':message}),flush=True)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--image',required=True);parser.add_argument('--output',required=True);parser.add_argument('--seed',type=int,default=42);parser.add_argument('--steps',type=int,default=50);parser.add_argument('--resolution',type=int,default=256);parser.add_argument('--guidance',type=float,default=5);parser.add_argument('--offload',action='store_true');args=parser.parse_args()
    output=Path(args.output);output.mkdir(parents=True,exist_ok=True)
    if (output/'original.glb').exists():raise RuntimeError('Preserve prior output; choose a new directory.')
    import torch,numpy as np,psutil
    from PIL import Image
    from safetensors.torch import save_file
    from hy3dgen.shapegen import Hunyuan3DDiTFlowMatchingPipeline
    from backend.mesh_quality import inspect_mesh
    if not torch.cuda.is_available():raise RuntimeError('CUDA unavailable.')
    started=time.perf_counter();torch.cuda.reset_peak_memory_stats()
    weights=ROOT/'models/hunyuan-mini/hunyuan3d-dit-v2-mini'
    stage('Hunyuan-mini: loading official local FP16 shape model')
    pipe=Hunyuan3DDiTFlowMatchingPipeline.from_single_file(str(weights/'model.fp16.safetensors'),str(weights/'config.yaml'),device='cpu' if args.offload else 'cuda',dtype=torch.float16,use_safetensors=True)
    if args.offload:pipe.enable_model_cpu_offload(gpu_id=0)
    load_seconds=time.perf_counter()-started
    image=Image.open(args.image).convert('RGBA')
    native=pipe.prepare_image(image)
    rgb=((native['image'][0].permute(1,2,0).numpy()+1)*127.5).clip(0,255).astype(np.uint8)
    alpha=((native['mask'][0,0].numpy()+1)*127.5).clip(0,255).astype(np.uint8)
    Image.fromarray(rgb).save(output/'prepared.png');Image.fromarray(np.dstack([rgb,alpha])).save(output/'prepared_alpha.png')
    def callback(index,timestep,values):
        stage(f'Hunyuan-mini: diffusion {index+1}/{args.steps}')
        if index==args.steps-1:save_file({'latents':values.prev_sample.detach().cpu().contiguous()},str(output/'latents.safetensors'))
    stage('Hunyuan-mini: real shape inference')
    with torch.inference_mode():
        meshes=pipe(image=image,num_inference_steps=args.steps,guidance_scale=args.guidance,generator=torch.Generator(device='cuda').manual_seed(args.seed),octree_resolution=args.resolution,num_chunks=8000,mc_algo='mc',callback=callback,callback_steps=1)
    mesh=meshes[0]
    if mesh is None or not len(mesh.faces) or not np.isfinite(mesh.vertices).all():raise RuntimeError('No valid mesh; no fallback.')
    mesh.vertex_normals;mesh.export(output/'original.glb',include_normals=True);mesh.export(output/'raw_generation.glb',include_normals=True)
    torch.cuda.synchronize()
    report={'provider':'hunyuan_mini','experimental':True,'seed':args.seed,'seed_supported':True,'device':torch.cuda.get_device_name(0),'dtype':'float16','input_batch':1,'cfg_batch':2,'num_inference_steps':args.steps,'guidance_scale':args.guidance,'mc_resolution':args.resolution,'model_cpu_offload':args.offload,'encoder_resolution':518,'raw_generation':True,'auto_decimated':False,'native_textures':False,'texture':{'method':'none','generated':False},'coordinate_system':'y_up','render_front_axis':'negative_y','triangles':len(mesh.faces),'dimensions':mesh.extents.tolist(),'integrity':inspect_mesh(mesh.vertices,mesh.faces,normals=mesh.vertex_normals),'peak_vram_mb':round(torch.cuda.max_memory_allocated()/1024**2,1),'peak_reserved_mb':round(torch.cuda.max_memory_reserved()/1024**2,1),'process_rss_mb':round(psutil.Process().memory_info().rss/1024**2,1),'load_seconds':round(load_seconds,2),'total_seconds':round(time.perf_counter()-started,2),'original_sha256':hashlib.sha256((output/'original.glb').read_bytes()).hexdigest(),'source_sha256':hashlib.sha256(Path(args.image).read_bytes()).hexdigest(),'offline_network_blocked':True}
    (output/'inference.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report),flush=True)

if __name__=='__main__':
    from backend.instance import InstanceLock
    lock=InstanceLock(ROOT/'data/gpu.lock');lock.acquire()
    try:main()
    finally:lock.release()
