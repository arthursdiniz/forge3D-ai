"""Offline, serial real TripoSG shape inference. No texturing claims."""
import argparse
import hashlib
import json
import os
import socket
import sys
import time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_HUB_DISABLE_TELEMETRY='1',U2NET_HOME=str(ROOT/'models/rembg'),CUBLAS_WORKSPACE_CONFIG=':4096:8')
def no_network(*args,**kwargs):raise RuntimeError('Rede bloqueada durante inferência local.')
socket.socket.connect=no_network;socket.create_connection=no_network
def stage(value,**extra):print(json.dumps({'stage':value,**extra}),flush=True)

def generate_candidate(image,output,options,pipe,settings,load_seconds=0):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    if (output/'original.glb').exists():raise RuntimeError('Preserve existing SG generation.')
    import torch,numpy as np,psutil
    from PIL import Image
    from safetensors.torch import save_file
    from backend.preprocess import prepare_image
    from backend.triposg_runtime import TripoSGRuntime
    from backend.mesh_quality import inspect_mesh
    from backend.quality_settings import generation_settings
    if not torch.cuda.is_available():raise RuntimeError('CUDA indisponível.')
    started=time.perf_counter();torch.cuda.reset_peak_memory_stats()
    seed=int(options.get('seed') if options.get('seed') is not None else 42)
    if not 0<=seed<=4294967295:raise ValueError('Seed deve estar entre 0 e 4294967295.')
    if options.get('foreground_ratio') is not None and not 0.5<=options['foreground_ratio']<=0.875:raise ValueError('TripoSG: ocupação deve estar entre 50% e 87,5% para preservar o crop do encoder.')
    torch.manual_seed(seed);np.random.seed(seed)
    stage('Preparando imagem TripoSG: fundo branco e alpha preservado')
    preparation=prepare_image(Path(image),output/'prepared.png',foreground_ratio=options.get('foreground_ratio') or 5/6,crop=options.get('crop'),remove_background=options.get('remove_background',False),model_dir=ROOT/'models/rembg',background_mode=options.get('background_mode') or 'auto',preparation_preset=options.get('preparation_preset','prop'),background_color=(255,255,255),save_alpha=True,save_masked_source=True)
    (output/'preparation.json').write_text(json.dumps(preparation,indent=2),encoding='utf-8')
    prepared=Image.open(output/'prepared.png').convert('RGB')
    tensor=pipe.feature_extractor_dinov2(prepared,return_tensors='pt').pixel_values
    preparation['encoder_tensor_shape']=list(tensor.shape)
    mean=torch.tensor(pipe.feature_extractor_dinov2.image_mean).view(3,1,1)
    std=torch.tensor(pipe.feature_extractor_dinov2.image_std).view(3,1,1)
    encoder_rgb=(tensor[0]*std+mean).clamp(0,1).permute(1,2,0).numpy()
    Image.fromarray(np.rint(encoder_rgb*255).astype(np.uint8)).save(output/'prepared_encoder.png')
    preparation.update(encoder_input_sha256=hashlib.sha256((output/'prepared_encoder.png').read_bytes()).hexdigest(),encoder_normalization='ImageNet mean/std; BitImageProcessor crop224 from resize256')
    last_latents=None
    def callback(pipeline,index,timestep,values):
        nonlocal last_latents
        if index+1==settings['num_inference_steps']:
            last_latents=values['latents'].detach().cpu().contiguous()
            save_file({'latents':last_latents},str(output/'latents.safetensors'))
            stage('TripoSG: extração hierárquica da superfície')
        else:stage('TripoSG: difusão '+str(index+1)+'/'+str(settings['num_inference_steps']),step=index+1,total_steps=settings['num_inference_steps'])
        return values
    stage('TripoSG: inferência neural de forma')
    inference_start=time.perf_counter()
    with torch.inference_mode():
        result=pipe(image=prepared,generator=torch.Generator(device='cuda').manual_seed(seed),num_inference_steps=settings['num_inference_steps'],guidance_scale=settings['guidance_scale'],num_tokens=settings['num_tokens'],dense_octree_depth=settings['dense_octree_depth'],hierarchical_octree_depth=settings['hierarchical_octree_depth'],use_flash_decoder=False,callback_on_step_end=callback)
    mesh=result.meshes[0]
    if not len(mesh.faces) or not np.isfinite(mesh.vertices).all():raise RuntimeError('TripoSG não produziu malha válida. Sem fallback.')
    mesh.vertex_normals
    mesh.export(output/'original.glb',include_normals=True);mesh.export(output/'raw_generation.glb',include_normals=True)
    torch.cuda.synchronize()
    weights=json.loads((ROOT/'models/triposg/download_manifest.json').read_text())
    metadata={'provider':'triposg','pipeline_version':1,'code_revision':'fc5c40990181e2a756c4e0b1c2f4d6b5202faf8c','weight_revision':weights['revision'],'weight_files':weights['files'],'device':torch.cuda.get_device_name(0),'torch':torch.__version__,'cuda':torch.version.cuda,'seed':seed,'seed_supported':True,'input_batch':1,'cfg_batch':2,'triangles':len(mesh.faces),'vertices':len(mesh.vertices),'dimensions':mesh.extents.tolist(),'coordinate_system':'y_up','render_front_axis':'negative_y','effective_settings':settings,'parameters':options,'image_preparation':preparation,'texture':{'method':'none','generated':False,'pbr_channels':[]},'native_uvs':False,'native_textures':False,'offline_network_blocked':True,'raw_generation':True,'auto_decimated':False,'peak_vram_mb':round(torch.cuda.max_memory_allocated()/1024**2,1),'peak_reserved_mb':round(torch.cuda.max_memory_reserved()/1024**2,1),'process_rss_mb':round(psutil.Process().memory_info().rss/1024**2,1),'load_seconds':round(load_seconds,2),'inference_seconds':round(time.perf_counter()-inference_start,2),'total_seconds':round(time.perf_counter()-started+load_seconds,2),'integrity':[inspect_mesh(mesh.vertices,mesh.faces,normals=mesh.vertex_normals)],'warnings':preparation['warnings']+['TripoSG gera somente geometria; UVs/material neutro são pós-processamento Blender, sem textura gerada.'],'original_sha256':hashlib.sha256((output/'original.glb').read_bytes()).hexdigest()}
    (output/'inference.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8');(output/'preparation.json').write_text(json.dumps(preparation,indent=2),encoding='utf-8')
    stage('TripoSG: RAW real preservado')
    return metadata

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--image',required=True);parser.add_argument('--output',required=True);parser.add_argument('--options',required=True);args=parser.parse_args()
    output=Path(args.output);output.mkdir(parents=True,exist_ok=True)
    options=json.loads(Path(args.options).read_text(encoding='utf-8-sig'))
    from backend.triposg_runtime import TripoSGRuntime
    from backend.quality_settings import generation_settings
    base=generation_settings(options.get('quality','balanced'),'triposg')
    settings={**base,'num_inference_steps':int(options.get('num_inference_steps',base['num_inference_steps'])),'guidance_scale':float(options.get('guidance_scale',base['guidance_scale'])),'dense_octree_depth':int(options.get('dense_octree_depth',base['dense_octree_depth'])),'hierarchical_octree_depth':int(options.get('hierarchical_octree_depth',base['hierarchical_octree_depth'])),'use_flash_decoder':False,'decoder_chunk':int(options.get('decoder_chunk',base['decoder_chunk'])),'model_cpu_offload':bool(options.get('model_cpu_offload',base['model_cpu_offload'])),'dtype':'float16'}
    settings.update(mc_resolution=2**settings['hierarchical_octree_depth'],texture_resolution=None,texture_method='none')
    if not 1<=settings['num_inference_steps']<=100 or not 1<=settings['guidance_scale']<=15 or not 5<=settings['dense_octree_depth']<=settings['hierarchical_octree_depth']<=9 or not 1024<=settings['decoder_chunk']<=50000:raise ValueError('Configuração TripoSG inválida.')
    if options.get('quality_mode'):
        from backend.character_advanced import run_advanced
        run_advanced(ROOT,Path(args.image),output,options,settings,provider='triposg');return
    started=time.perf_counter();runtime=TripoSGRuntime(ROOT)
    stage('Carregando TripoSG oficial local')
    pipe=runtime.load(settings['model_cpu_offload'],settings['decoder_chunk'])
    try:generate_candidate(Path(args.image),output,options,pipe,settings,time.perf_counter()-started)
    finally:del pipe;runtime.unload()

if __name__=='__main__':
    from backend.instance import InstanceLock
    gpu_lock=InstanceLock(ROOT/'data/gpu.lock',message='GPU ocupada por outra inferência Forge3D.')
    try:
        for attempt in range(600):
            try:gpu_lock.acquire();break
            except RuntimeError:
                if not attempt:stage('Aguardando liberação da GPU')
                time.sleep(1)
        else:raise RuntimeError('GPU ocupada por mais de 10 minutos.')
        main()
    except Exception as error:
        message=str(error)
        if 'out of memory' in message.lower():message='CUDA OOM no TripoSG; arquivos já gravados mantidos. Configuração não validada para esta memória. '+message
        print(json.dumps({'error':message}),flush=True)
        import traceback;traceback.print_exc();sys.exit(1)
    finally:gpu_lock.release()
