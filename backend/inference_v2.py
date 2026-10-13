"""Quality pipeline: real neural field, native UV/texel samples, immutable raw."""
import argparse
import hashlib
import json
import os
import socket
import sys
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_HUB_DISABLE_TELEMETRY='1',U2NET_HOME=str(ROOT/'models/rembg'))
def no_network(*args,**kwargs):raise RuntimeError('Rede bloqueada durante inferência.')
socket.socket.connect=no_network
socket.create_connection=no_network
def stage(value):print(json.dumps({'stage':value}),flush=True)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--image',required=True);parser.add_argument('--output',required=True);parser.add_argument('--options',required=True)
    parser.add_argument('--ablation-resolution',type=int,choices=[128,192,256,320])
    args=parser.parse_args()
    output=Path(args.output);output.mkdir(parents=True,exist_ok=True)
    options=json.loads(Path(args.options).read_text(encoding='utf-8-sig'))
    started=time.perf_counter()
    import torch
    import numpy as np
    from PIL import Image
    from safetensors.torch import save_file
    from backend.preprocess import prepare_image
    from backend.quality_settings import generation_settings
    from backend.triposr_runtime import TripoSRRuntime
    from backend.neural_texture import bake_neural_texture
    from backend.color_space import srgb_to_linear
    settings=generation_settings(options.get('quality','balanced'))
    if args.ablation_resolution:settings['mc_resolution']=args.ablation_resolution
    settings['texture_resolution']=options.get('texture_resolution') or settings['texture_resolution']
    geometry_only=options.get('texture_output')=='geometry_only'
    if geometry_only:settings.update(texture_method='none',texture_resolution=None)
    stage('Preparando referência, preservando alpha')
    prepared=output/'prepared.png'
    image_report=prepare_image(Path(args.image),prepared,options.get('foreground_ratio'),options.get('crop'),options.get('remove_background',False),ROOT/'models/rembg',options.get('background_mode'),options.get('preparation_preset','prop'),save_alpha=True,save_masked_source=True)
    (output/'preparation.json').write_text(json.dumps(image_report,indent=2),encoding='utf-8')
    if not torch.cuda.is_available():raise RuntimeError('CUDA indisponível.')
    free,total=torch.cuda.mem_get_info()
    if free<3*1024**3:raise RuntimeError('Menos de 3 GB livres. Feche aplicativos GPU antes de gerar.')
    torch.cuda.reset_peak_memory_stats()
    stage('Carregando TripoSR local')
    runtime=TripoSRRuntime(ROOT)
    model=runtime.load()
    load_seconds=time.perf_counter()-started
    neural_start=time.perf_counter()
    stage('Inferência neural de geometria')
    with torch.inference_mode():
        codes=model([Image.open(prepared).convert('RGB')],device='cuda')
        save_file({'scene_codes':codes.cpu().contiguous()},str(output/'scene_codes.safetensors'))
        stage('Extraindo superfície sem decimation')
        mesh=model.extract_mesh(codes,has_vertex_color=not geometry_only,resolution=settings['mc_resolution'])[0]
    if not len(mesh.faces) or not np.isfinite(mesh.vertices).all():raise RuntimeError('Geometria inválida.')
    # Explicit normals prevent Blender treating the raw surface as flat facets.
    mesh.vertex_normals
    if not geometry_only:
        colors=mesh.visual.vertex_colors.copy()
        colors[:,:3]=np.clip(np.rint(srgb_to_linear(colors[:,:3]/255.0)*255),0,255).astype(np.uint8)
        mesh.visual.vertex_colors=colors
    mesh.export(output/'original.glb',include_normals=True)
    mesh.export(output/'raw_generation.glb',include_normals=True)
    geometry_seconds=time.perf_counter()-neural_start
    texture={ 'method':'vertex_bake','vertex_color_interpolation':True,'pbr_channels':['base_color'] }
    if geometry_only:texture={'method':'none','vertex_color_interpolation':False,'pbr_channels':[]}
    if settings['texture_method']=='neural_atlas':
        stage('UV xatlas e amostragem neural por texel')
        def query_colors(positions):
            with torch.inference_mode():
                xyz=torch.as_tensor(positions,dtype=torch.float32,device='cuda')
                return model.renderer.query_triplane(model.decoder,xyz,codes[0])['color'].cpu().numpy()
        texture=bake_neural_texture(mesh,query_colors,settings['texture_resolution'],output/'textures')
    texture['raw_vertex_color_space']='absent; no color query' if geometry_only else 'sRGB neural RGB converted to linear glTF COLOR_0, 8-bit quantized'
    torch.cuda.synchronize()
    manifest=json.loads((ROOT/'models/manifest.json').read_text())
    metadata={'provider':'triposr','pipeline_version':2,'code_revision':'107cefdc244c39106fa830359024f6a2f1c78871','weight_revision':manifest['weight_revision'],'weight_sha256':manifest['files'][1]['sha256'],'device':torch.cuda.get_device_name(0),'torch':torch.__version__,'cuda':torch.version.cuda,'peak_vram_mb':round(torch.cuda.max_memory_allocated()/1024**2,1),'peak_reserved_mb':round(torch.cuda.max_memory_reserved()/1024**2,1),'load_seconds':round(load_seconds,2),'inference_seconds':round(geometry_seconds,2),'total_seconds':round(time.perf_counter()-started,2),'triangles':len(mesh.faces),'vertices':len(mesh.vertices),'dimensions':mesh.extents.tolist(),'vertex_colors':not geometry_only,'offline_network_blocked':True,'marching_cubes':'scikit-image CPU; neural CUDA','texture':texture,'image_preparation':image_report,'parameters':options,'effective_settings':settings,'coordinate_system':'z_up','warnings':image_report['warnings'],'raw_generation':True,'auto_decimated':False,'seed':None,'seed_supported':False,'original_sha256':hashlib.sha256((output/'original.glb').read_bytes()).hexdigest()}
    (output/'inference.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
    del mesh,codes,model
    runtime.unload()
    stage('RAW e textura neural preservados')

if __name__=='__main__':
    from backend.instance import InstanceLock
    gpu_lock=InstanceLock(ROOT/'data/gpu.lock',message='GPU já está executando outra inferência Forge3D. Aguarde e tente novamente.')
    try:
        for attempt in range(600):
            try:
                gpu_lock.acquire()
                break
            except RuntimeError:
                if attempt==0:stage('Aguardando outra inferência local liberar a GPU')
                time.sleep(1)
        else:raise RuntimeError('GPU ocupada por mais de 10 minutos. Tente novamente após a inferência em curso.')
        main()
    except Exception as error:
        message=str(error)
        if 'out of memory' in message.lower():message='CUDA OOM: arquivos já gravados foram mantidos. Feche outros aplicativos ou selecione FAST e tente novamente. '+message
        print(json.dumps({'error':message}),flush=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:gpu_lock.release()
