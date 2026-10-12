"""Unvalidated optional official adapter. Provider stays gated until real local proof."""
import argparse,json,os,socket,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'vendor/SPAR3D'))
os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',SPAR3D_LOW_VRAM='1')
def forbidden(*args,**kwargs):raise RuntimeError('Network blocked during optional local inference.')
socket.socket.connect=forbidden;socket.create_connection=forbidden
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--image',required=True);parser.add_argument('--output',required=True);parser.add_argument('--options',required=True);args=parser.parse_args()
    if not (ROOT/'models/spar3d/license_acceptance.json').is_file():raise RuntimeError('Restricted model access/license not authorized.')
    import torch,trimesh
    from PIL import Image
    from spar3d.system import SPAR3D
    from spar3d.utils import foreground_crop
    from backend.mesh_quality import inspect_mesh
    from backend.config import atomic_json
    directory=Path(args.output).resolve();directory.mkdir(parents=True,exist_ok=True)
    if (directory/'original.glb').exists():raise RuntimeError('Preserve prior generation.')
    image=Image.open(args.image).convert('RGBA')
    if image.getchannel('A').getextrema()[0]==255:raise ValueError('SPAR3D optional adapter requires a real supplied alpha mask; background model is not downloaded implicitly.')
    options=json.loads(Path(args.options).read_text(encoding='utf-8-sig'));started=time.perf_counter();torch.cuda.reset_peak_memory_stats()
    model=SPAR3D.from_pretrained(str(ROOT/'models/spar3d'),config_name='config.yaml',weight_name='model.safetensors',low_vram_mode=True);model.to('cuda');model.eval()
    image=foreground_crop(image,1.3);image.save(directory/'prepared.png');image.save(directory/'prepared_alpha.png')
    try:
        with torch.no_grad(),torch.autocast(device_type='cuda',dtype=torch.bfloat16):mesh,details=model.run_image([image],bake_resolution=options.get('texture_resolution') or 1024,remesh='none',vertex_count=-1,return_points=True)
        if isinstance(mesh,list):mesh=mesh[0]
        mesh.export(directory/'original.glb',include_normals=True);mesh.export(directory/'raw_generation.glb',include_normals=True);mesh.export(directory/'textured_generation.glb',include_normals=True)
        details['point_clouds'][0].export(directory/'points.ply');torch.cuda.synchronize()
        prep={'method':'native foreground_crop','foreground_ratio':1.3,'background_action':'preserved_alpha','warnings':[]}
        metadata={'provider':'spar3d','coordinate_system':'y_up','render_front_axis':'negative_y','seed_supported':False,'texture':{'method':'native_spar3d','generated':True},'image_preparation':prep,'effective_settings':{'texture_resolution':options.get('texture_resolution') or 1024,'model_cpu_offload':True,'remesh':'none'},'triangles':len(mesh.faces),'integrity':[inspect_mesh(mesh.vertices,mesh.faces,normals=mesh.vertex_normals)],'peak_vram_mb':round(torch.cuda.max_memory_allocated()/1024**2,1),'peak_reserved_mb':round(torch.cuda.max_memory_reserved()/1024**2,1),'total_seconds':round(time.perf_counter()-started,2),'offline_network_blocked':True,'warnings':['Optional SPAR3D adapter requires local validation before provider activation.']}
        atomic_json(directory/'inference.json',metadata);atomic_json(directory/'preparation.json',prep)
    finally:del model;import gc;gc.collect();torch.cuda.empty_cache()
if __name__=='__main__':
    from backend.instance import InstanceLock
    lock=InstanceLock(ROOT/'data/gpu.lock')
    try:lock.acquire();main()
    finally:lock.release()
