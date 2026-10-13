import argparse
import json
import sys
import os
import socket
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
sys.path.append(str(ROOT/'.venv/Lib/site-packages'))
os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_HUB_DISABLE_TELEMETRY='1')
def no_network(*args,**kwargs):raise RuntimeError('Network disabled during independent texturing.')
socket.socket.connect=no_network;socket.create_connection=no_network

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--input',required=True);parser.add_argument('--output',required=True);parser.add_argument('--options',required=True);args=parser.parse_args()
    from backend.instance import InstanceLock
    lock=InstanceLock(ROOT/'data/gpu.lock')
    lock.acquire()
    try:
        from backend.texture_engine.contracts import TextureOptions
        from backend.texture_engine.providers import TextureProvider
        import numpy as np
        import trimesh
        from PIL import Image
        directory=Path(args.output);options=TextureOptions.model_validate_json(Path(args.options).read_text(encoding='utf-8')).model_dump()
        print(json.dumps({'stage':'Texture Engine: preparing UV and references'}),flush=True)
        bundle=json.loads((directory/'texture_references.json').read_text(encoding='utf-8'));references={}
        for view,record in bundle['views'].items():
            path=(directory/record['path']).resolve()
            if not path.is_relative_to(directory.resolve()):raise ValueError('Unsafe reference path.')
            image=Image.open(path).convert('RGBA')
            if options['background_mode']=='remove':
                import os
                from rembg import remove,new_session
                if not (ROOT/'models/rembg/u2netp.onnx').is_file():raise ValueError('Local u2netp weights missing; run modeling setup.')
                os.environ['U2NET_HOME']=str(ROOT/'models/rembg')
                image=remove(image,session=new_session('u2netp',providers=['CPUExecutionProvider']))
            if image.getchannel('A').getextrema()[0]==255:raise ValueError('Reference has no foreground alpha mask.')
            references[view]=np.asarray(image)
        from backend.texture_engine.import_safety import validate_resources
        validate_resources('model.glb',Path(args.input).read_bytes(),{})
        scene=trimesh.load(args.input,force='scene',process=False)
        provider=TextureProvider(ROOT,options['provider'])
        try:
            provider.prepare(scene,references,options,directory);provider.generate()
            print(json.dumps({'stage':'Texture Engine: depth-tested fusion and GLB identity'}),flush=True)
            provider.finalize()
            print(json.dumps({'stage':'Texture Engine: geometry verified'}),flush=True)
        finally:provider.release()
    finally:lock.release()

if __name__=='__main__':main()
