"""Opt-in texture projection after selecting geometry; unknown surfaces stay neutral."""
import argparse,json,sys,time,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--input',required=True);parser.add_argument('--output',required=True);parser.add_argument('--references',required=True);parser.add_argument('--resolution',type=int,default=1024);parser.add_argument('--front-axis',default='negative_y');parser.add_argument('--front-only',action='store_true');args=parser.parse_args()
    import trimesh
    from PIL import Image
    from backend.reference_atlas import bake_reference_views
    from backend.config import atomic_json
    directory=Path(args.output).resolve();directory.mkdir(parents=True,exist_ok=True)
    manifest=json.loads(Path(args.references).read_text(encoding='utf-8'));images={}
    for name,item in manifest['views'].items():
        if args.front_only and name!='front':continue
        images[name]=Image.open(item.get('masked_path',item['path'])).convert('RGBA')
    report=bake_reference_views(trimesh.load(args.input,force='scene',process=False),images,args.resolution,directory/'model.glb',args.front_axis)
    report['source_sha256']=hashlib.sha256(Path(args.input).read_bytes()).hexdigest();atomic_json(directory/'texture_projection.json',report)
if __name__=='__main__':
    from backend.instance import InstanceLock
    lock=InstanceLock(ROOT/'data/gpu.lock')
    try:lock.acquire();main()
    finally:lock.release()
