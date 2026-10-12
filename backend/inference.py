"""Real TripoSR neural inference. Entire process is offline and disposable."""
import argparse
import hashlib
import json
import os
import socket
import sys
import time
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_HUB_DISABLE_TELEMETRY='1',U2NET_HOME=str(ROOT/'models/rembg'))
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/'vendor/TripoSR'))

def forbid_network(*args,**kwargs):
    raise RuntimeError('Rede desabilitada durante inferência local.')

socket.socket.connect = forbid_network
socket.create_connection = forbid_network

def stage(name):
    print(json.dumps({'stage':name}),flush=True)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--image',required=True)
    parser.add_argument('--output',required=True)
    parser.add_argument('--options',required=True)
    args = parser.parse_args()
    output = Path(args.output)
    output.mkdir(parents=True,exist_ok=True)
    options = json.loads(Path(args.options).read_text(encoding='utf-8-sig'))
    started = time.perf_counter()
    import numpy as np
    import torch
    from skimage.measure import marching_cubes
    # Official helper swaps z/y/x. Return torchmcubes' z/y/x convention.
    shim = types.ModuleType('torchmcubes')
    def cpu_marching(level, threshold):
        vertices, faces, _, _ = marching_cubes(level.detach().cpu().numpy(),level=threshold)
        return torch.from_numpy(vertices[:,[2,1,0]].copy()),torch.from_numpy(faces.copy().astype(np.int64))
    shim.marching_cubes = cpu_marching
    sys.modules['torchmcubes'] = shim
    from backend.preprocess import prepare_image
    stage('Preparando imagem')
    prepared = output / 'prepared.png'
    prepare_image(Path(args.image),prepared,options.get('foreground_ratio',0.85),options.get('crop'),options.get('remove_background',False),ROOT/'models/rembg')
    if not torch.cuda.is_available():
        raise RuntimeError('CUDA indisponível. Verifique driver NVIDIA e instalação PyTorch CUDA.')
    free,total = torch.cuda.mem_get_info()
    if free < 2.5 * 1024**3:
        raise RuntimeError('Pouca VRAM disponível. Feche outros aplicativos GPU antes de gerar.')
    torch.cuda.reset_peak_memory_stats()
    from tsr.system import TSR
    from tsr.models.tokenizers import image as tokenizer
    from omegaconf import OmegaConf
    from PIL import Image
    def local_dino(repo_id,filename,**kwargs):
        if repo_id!='facebook/dino-vitb16' or filename!='config.json':
            raise RuntimeError('Dependência de encoder inesperada')
        return str(ROOT/'models/dino/config.json')
    tokenizer.hf_hub_download = local_dino
    stage('Carregando TripoSR na GPU')
    config = OmegaConf.load(ROOT/'models/triposr/config.yaml')
    OmegaConf.resolve(config)
    model = TSR(config)
    weights = torch.load(ROOT/'models/triposr/model.ckpt',map_location='cpu',weights_only=True)
    model.load_state_dict(weights)
    del weights
    model.eval().to('cuda')
    model.renderer.set_chunk_size(4096)
    load_seconds = time.perf_counter()-started
    stage('Inferência neural na RTX 4060')
    resolution = {'draft':128,'balanced':192,'high':256}[options.get('quality','balanced')]
    infer_start = time.perf_counter()
    with torch.inference_mode():
        codes = model([Image.open(prepared).convert('RGB')],device='cuda')
        stage('Extraindo geometria e cores neurais')
        mesh = model.extract_mesh(codes,has_vertex_color=True,resolution=resolution)[0]
    torch.cuda.synchronize()
    if not len(mesh.faces) or not np.isfinite(mesh.vertices).all():
        raise RuntimeError('IA produziu geometria vazia ou inválida; tente outra referência.')
    original = output/'original.glb'
    mesh.export(original)
    manifest = json.loads((ROOT/'models/manifest.json').read_text())
    metadata = {'provider':'triposr','code_revision':'107cefdc244c39106fa830359024f6a2f1c78871','weight_revision':manifest['weight_revision'],'weight_sha256':manifest['files'][1]['sha256'],'device':torch.cuda.get_device_name(0),'torch':torch.__version__,'cuda':torch.version.cuda,'peak_vram_mb':round(torch.cuda.max_memory_allocated()/1024**2,1),'peak_reserved_mb':round(torch.cuda.max_memory_reserved()/1024**2,1),'load_seconds':round(load_seconds,2),'inference_seconds':round(time.perf_counter()-infer_start,2),'total_seconds':round(time.perf_counter()-started,2),'triangles':len(mesh.faces),'vertices':len(mesh.vertices),'dimensions':mesh.extents.tolist(),'vertex_colors':True,'offline_network_blocked':True,'marching_cubes':'scikit-image CPU, neural network CUDA','source_sha256':hashlib.sha256(Path(args.image).read_bytes()).hexdigest(),'original_sha256':hashlib.sha256(original.read_bytes()).hexdigest(),'parameters':options}
    (output/'inference.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
    stage('Geometria original salva')
    del mesh,codes,model
    torch.cuda.empty_cache()

if __name__=='__main__':
    from backend.instance import InstanceLock
    gpu_lock=InstanceLock(ROOT/'data/gpu.lock',message='GPU ocupada por outra inferência Forge3D. Aguarde.')
    try:
        gpu_lock.acquire()
        main()
    except Exception as error:
        message = str(error)
        if 'out of memory' in message.lower():
            message = 'Memória CUDA insuficiente. Feche outros aplicativos e use o preset Rápido. '+message
        print(json.dumps({'error':message}),flush=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:gpu_lock.release()
