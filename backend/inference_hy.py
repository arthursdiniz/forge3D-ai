"""Offline native Hunyuan shape inference, one candidate at a time."""
import argparse
import hashlib
import json
import os
import socket
import sys
import time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_HUB_DISABLE_TELEMETRY='1')
def no_network(*args,**kwargs):raise RuntimeError('Rede bloqueada durante inferência local.')
socket.socket.connect=no_network;socket.create_connection=no_network
def stage(message):print(json.dumps({'stage':message}),flush=True)

def generate_candidate(image,output,options,pipe,settings,load_seconds=0):
    import torch,numpy as np,psutil
    from PIL import Image
    from safetensors.torch import save_file
    from backend.preprocess import prepare_image
    from backend.mesh_quality import inspect_mesh
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    if (output/'original.glb').exists():raise RuntimeError('Saída já existe; preserve a geração anterior.')
    started=time.perf_counter();torch.cuda.reset_peak_memory_stats()
    ratio=options.get('foreground_ratio') or .85
    preparation=prepare_image(Path(image),output/'prepared.png',ratio,options.get('crop'),options.get('remove_background',False),ROOT/'models/rembg',options.get('background_mode') or 'auto',options.get('preparation_preset','character'),background_color=(255,255,255),save_masked_source=True)
    masked=Image.open(output/'prepared_masked.png').convert('RGBA')
    pipe.image_processor.border_ratio=1-ratio
    native=pipe.prepare_image(masked)
    rgb=((native['image'][0].permute(1,2,0).numpy()+1)*127.5).clip(0,255).astype(np.uint8)
    alpha=((native['mask'][0,0].numpy()+1)*127.5).clip(0,255).astype(np.uint8)
    Image.fromarray(rgb).save(output/'prepared.png');Image.fromarray(np.dstack([rgb,alpha])).save(output/'prepared_alpha.png')
    encoder=pipe.conditioner.main_image_encoder.transform((native['image']+1)/2)
    preview=(encoder[0]*torch.tensor([.229,.224,.225]).view(3,1,1)+torch.tensor([.485,.456,.406]).view(3,1,1)).clamp(0,1).permute(1,2,0).numpy()
    Image.fromarray(np.rint(preview*255).astype(np.uint8)).save(output/'prepared_encoder.png')
    preparation.update(encoder_tensor_shape=list(encoder.shape),encoder_normalization='Native DINO giant518/ImageNet; original masked input preserved without early downsampling',foreground_ratio=ratio,native_processor='ImageProcessorV2',effective_sha256=hashlib.sha256((output/'prepared.png').read_bytes()).hexdigest())
    seed=options.get('seed') if options.get('seed') is not None else 42
    def callback(index,timestep,values):
        stage(f'Hunyuan-mini: difusão {index+1}/{settings["num_inference_steps"]}')
        if index==settings['num_inference_steps']-1:save_file({'latents':values.prev_sample.detach().cpu().contiguous()},str(output/'latents.safetensors'))
    stage('Hunyuan-mini: inferência real de forma')
    with torch.inference_mode():
        meshes=pipe(image=masked,num_inference_steps=settings['num_inference_steps'],guidance_scale=settings['guidance_scale'],generator=torch.Generator(device='cuda').manual_seed(seed),octree_resolution=settings['mc_resolution'],num_chunks=settings['num_chunks'],mc_algo='mc',callback=callback,callback_steps=1)
    mesh=meshes[0]
    if mesh is None or not len(mesh.faces) or not np.isfinite(mesh.vertices).all():raise RuntimeError('Geometria inválida; sem fallback.')
    mesh.vertex_normals;mesh.export(output/'original.glb',include_normals=True);mesh.export(output/'raw_generation.glb',include_normals=True);torch.cuda.synchronize()
    manifest=json.loads((ROOT/'models/hunyuan-mini/download_manifest.json').read_text())
    metadata={'provider':'hunyuan_mini','pipeline_version':1,'code_revision':manifest['code_revision'],'weight_revision':manifest['revision'],'license':'Tencent Hunyuan Community — teste pessoal local autorizado','seed':seed,'seed_supported':True,'device':torch.cuda.get_device_name(0),'torch':torch.__version__,'cuda':torch.version.cuda,'input_batch':1,'cfg_batch':2,'effective_settings':settings,'parameters':options,'image_preparation':preparation,'texture':{'method':'none','generated':False},'coordinate_system':'y_up','render_front_axis':'negative_y','raw_generation':True,'auto_decimated':False,'native_uvs':False,'native_textures':False,'triangles':len(mesh.faces),'vertices':len(mesh.vertices),'dimensions':mesh.extents.tolist(),'integrity':[inspect_mesh(mesh.vertices,mesh.faces,normals=mesh.vertex_normals)],'peak_vram_mb':round(torch.cuda.max_memory_allocated()/1024**2,1),'peak_reserved_mb':round(torch.cuda.max_memory_reserved()/1024**2,1),'process_rss_mb':round(psutil.Process().memory_info().rss/1024**2,1),'load_seconds':round(load_seconds,2),'inference_seconds':round(time.perf_counter()-started,2),'total_seconds':round(time.perf_counter()-started+load_seconds,2),'offline_network_blocked':True,'original_sha256':hashlib.sha256((output/'original.glb').read_bytes()).hexdigest(),'warnings':preparation['warnings']+['Hunyuan-mini gera forma sem rig ou textura nativa; licença Tencent para o teste pessoal local.']}
    (output/'inference.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8');(output/'preparation.json').write_text(json.dumps(preparation,indent=2),encoding='utf-8')
    return metadata

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--image',required=True);parser.add_argument('--output',required=True);parser.add_argument('--options',required=True);args=parser.parse_args()
    options=json.loads(Path(args.options).read_text(encoding='utf-8-sig'))
    from backend.schemas import GenerationOptions
    from backend.quality_settings import generation_settings,validate_provider_options
    from backend.hunyuan_runtime import HunyuanMiniRuntime
    validated=GenerationOptions(**options);validate_provider_options('hunyuan_mini',validated)
    settings=generation_settings(validated.quality,'hunyuan_mini')
    if validated.quality=='advanced' or validated.quality_mode:
        from backend.character_advanced import run_advanced
        run_advanced(ROOT,Path(args.image),Path(args.output),validated.model_dump(),settings)
        return
    started=time.perf_counter();runtime=HunyuanMiniRuntime(ROOT);stage('Carregando Hunyuan-mini oficial local');pipe=runtime.load()
    try:generate_candidate(Path(args.image),Path(args.output),validated.model_dump(),pipe,settings,time.perf_counter()-started)
    finally:del pipe;runtime.unload()

if __name__=='__main__':
    from backend.instance import InstanceLock
    lock=InstanceLock(ROOT/'data/gpu.lock')
    try:
        for attempt in range(600):
            try:lock.acquire();break
            except RuntimeError:
                if not attempt:stage('Aguardando outra inferência local liberar GPU')
                time.sleep(1)
        else:raise RuntimeError('GPU ocupada por mais de10min.')
        main()
    finally:lock.release()
