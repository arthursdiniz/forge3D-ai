"""Pinned native multiview inference; every named image conditions the model."""
import argparse,hashlib,json,os,socket,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_HUB_DISABLE_TELEMETRY='1')
def forbidden(*args,**kwargs):raise RuntimeError('Rede bloqueada durante inferência local.')
socket.socket.connect=forbidden;socket.create_connection=forbidden
def stage(message):print(json.dumps({'stage':message}),flush=True)

class HunyuanMVRuntime:
    def __init__(self,root):self.root=Path(root);self.pipeline=None
    def load(self):
        import torch
        sys.path.insert(0,str(self.root/'vendor/Hunyuan3D-2'))
        from hy3dgen.shapegen import Hunyuan3DDiTFlowMatchingPipeline
        weights=self.root/'models/hunyuan-mv/hunyuan3d-dit-v2-mv'
        self.pipeline=Hunyuan3DDiTFlowMatchingPipeline.from_single_file(str(weights/'model.fp16.safetensors'),str(weights/'config.yaml'),device='cuda',dtype=torch.float16,use_safetensors=True)
        for module in [self.pipeline.model,self.pipeline.vae,self.pipeline.conditioner]:module.eval()
        return self.pipeline
    def unload(self):
        import gc,torch
        self.pipeline=None;gc.collect();torch.cuda.empty_cache()

def generate_candidate(image,output,options,pipe,settings,load_seconds=0):
    import torch,numpy as np,psutil
    from PIL import Image
    from safetensors.torch import save_file
    from backend.preprocess import prepare_image
    from backend.mesh_quality import inspect_mesh
    from backend.hunyuan_mv_provider import validate_native_views
    from backend.config import atomic_json
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=True)
    if (output/'original.glb').exists():raise RuntimeError('Preserve existing multiview generation.')
    refs=json.loads((output/'references.json').read_text(encoding='utf-8'))
    names=validate_native_views(refs['views']);started=time.perf_counter();torch.cuda.reset_peak_memory_stats()
    images={};preparations={};ratio=options.get('foreground_ratio') or .85
    for name in names:
        stage('Multiview: preparando vista '+name)
        target=output/'references'/name;target.mkdir(parents=True,exist_ok=True)
        entry=refs['views'][name];source=Path(entry['path'])
        preparation=prepare_image(source,target/'prepared.png',ratio,options.get('crop') if name=='front' else None,options.get('remove_background',False),ROOT/'models/rembg',options.get('background_mode') or 'auto',options.get('preparation_preset','character'),background_color=(255,255,255),save_alpha=True,save_masked_source=True)
        images[name]=Image.open(target/'prepared_masked.png').convert('RGBA')
        if images[name].getchannel('A').getextrema()[0]==255:raise ValueError('Multiview exige alpha/máscara real em cada vista; use remoção de fundo.')
        entry['masked_path']=str(target/'prepared_masked.png');preparations[name]=preparation
    # Native MVImageProcessorV2 consumes the dictionary, never a concatenated image.
    pipe.image_processor.border_ratio=1-ratio
    native=pipe.prepare_image(images)
    for index,name in enumerate(names):
        rgb=((native['image'][0,index].permute(1,2,0).numpy()+1)*127.5).clip(0,255).astype(np.uint8)
        Image.fromarray(rgb).save(output/'references'/name/'encoder_canvas.png')
    import shutil
    shutil.copy2(output/'references/front/prepared.png',output/'prepared.png')
    shutil.copy2(output/'references/front/prepared_alpha.png',output/'prepared_alpha.png')
    shutil.copy2(output/'references/front/prepared_masked.png',output/'prepared_masked.png')
    seed=options.get('seed') if options.get('seed') is not None else 42
    def callback(index,timestep,values):
        stage(f'Multiview: difusão {index+1}/{settings["num_inference_steps"]}')
        if index==settings['num_inference_steps']-1:save_file({'latents':values.prev_sample.detach().cpu().contiguous()},str(output/'latents.safetensors'))
    with torch.inference_mode():
        mesh=pipe(image=images,num_inference_steps=settings['num_inference_steps'],guidance_scale=settings['guidance_scale'],generator=torch.Generator(device='cuda').manual_seed(seed),octree_resolution=settings['mc_resolution'],num_chunks=settings['num_chunks'],mc_algo='mc',callback=callback,callback_steps=1)[0]
    if mesh is None or not len(mesh.faces) or not np.isfinite(mesh.vertices).all():raise RuntimeError('Geometria multiview inválida; sem fallback.')
    mesh.export(output/'original.glb',include_normals=True);mesh.export(output/'raw_generation.glb',include_normals=True);torch.cuda.synchronize()
    weights=json.loads((ROOT/'models/hunyuan-mv/download_manifest.json').read_text())
    preparation={**preparations['front'],'native_processor':'MVImageProcessorV2','native_multiview':True,'views':preparations,'encoder_tensor_shape':list(native['image'].shape),'foreground_ratio':ratio}
    metadata={'provider':'hunyuan_mv','pipeline_version':1,'code_revision':weights['code_revision'],'weight_revision':weights['revision'],'license':'Tencent Hunyuan Community — uso pessoal local autorizado','seed':seed,'seed_supported':True,'native_multiview':True,'conditioned_views':names,'reference_hashes':{name:refs['views'][name].get('sha256') for name in names},'device':torch.cuda.get_device_name(0),'torch':torch.__version__,'cuda':torch.version.cuda,'effective_settings':settings,'parameters':options,'image_preparation':preparation,'texture':{'method':'none','generated':False},'coordinate_system':'y_up','render_front_axis':'negative_y','raw_generation':True,'auto_decimated':False,'native_uvs':False,'native_textures':False,'triangles':len(mesh.faces),'vertices':len(mesh.vertices),'dimensions':mesh.extents.tolist(),'integrity':[inspect_mesh(mesh.vertices,mesh.faces,normals=mesh.vertex_normals)],'peak_vram_mb':round(torch.cuda.max_memory_allocated()/1024**2,1),'peak_reserved_mb':round(torch.cuda.max_memory_reserved()/1024**2,1),'process_rss_mb':round(psutil.Process().memory_info().rss/1024**2,1),'load_seconds':round(load_seconds,2),'inference_seconds':round(time.perf_counter()-started,2),'total_seconds':round(time.perf_counter()-started+load_seconds,2),'offline_network_blocked':True,'original_sha256':hashlib.sha256((output/'original.glb').read_bytes()).hexdigest(),'warnings':['Multiview nativo gera forma sem rig, UVs ou textura aprendida. Câmeras/poses incompatíveis podem deformar o modelo.']+list(dict.fromkeys(w for prep in preparations.values() for w in prep['warnings']))}
    atomic_json(output/'references.json',refs);atomic_json(output/'preparation.json',preparation);atomic_json(output/'inference.json',metadata)
    return metadata

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--image',required=True);parser.add_argument('--output',required=True);parser.add_argument('--options',required=True);args=parser.parse_args()
    from backend.schemas import GenerationOptions
    from backend.quality_settings import generation_settings,validate_provider_options
    options=GenerationOptions.model_validate_json(Path(args.options).read_text(encoding='utf-8-sig'));validate_provider_options('hunyuan_mv',options)
    settings=generation_settings(options.quality,'hunyuan_mv')
    if options.quality_mode:
        from backend.character_advanced import run_advanced
        run_advanced(ROOT,args.image,args.output,options.model_dump(),settings,'hunyuan_mv');return
    started=time.perf_counter();runtime=HunyuanMVRuntime(ROOT);stage('Multiview: carregando modelo oficial');pipe=runtime.load()
    try:generate_candidate(args.image,args.output,options.model_dump(),pipe,settings,time.perf_counter()-started)
    finally:del pipe;runtime.unload()
if __name__=='__main__':
    from backend.instance import InstanceLock
    lock=InstanceLock(ROOT/'data/gpu.lock')
    try:lock.acquire();main()
    finally:lock.release()
