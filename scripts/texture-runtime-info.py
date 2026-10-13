"""Record actual reused dependency metadata; no installation or remote access."""
import argparse
import hashlib
import importlib.metadata as metadata
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.append(str(ROOT/'.venv/Lib/site-packages'))
parser=argparse.ArgumentParser();parser.add_argument('--mode',choices=['core','neural'],required=True);args=parser.parse_args()
names=['numpy','trimesh','scipy','Pillow','xatlas','moderngl','pydantic']
if args.mode=='neural':names+=['torch','torchvision','diffusers','transformers','accelerate','einops','safetensors']
packages=[]
for name in names:
    dist=metadata.distribution(name);path=Path(dist._path)/'METADATA'
    packages.append({'name':name,'version':dist.version,'metadata_path':str(path.resolve()),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
record={'python':sys.version,'mode':args.mode,'packages':packages,'libraries_reused_read_only':True}
target=ROOT/'models/texture'/f'{args.mode}_runtime.json';target.parent.mkdir(parents=True,exist_ok=True);target.write_text(json.dumps(record,indent=2),encoding='utf-8')
print('TEXTURE_RUNTIME_LOCK_RECORDED '+args.mode)
