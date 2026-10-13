"""Atlas resolution QA using previously generated real neural views, no new inference."""
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
import trimesh
from PIL import Image
from backend.texture_engine.native import NativeControls
from backend.texture_engine.pipeline import texture_scene
source=ROOT/'data/assets/d50d2f098559482ca796bb59672b7289/model.glb'
scene=trimesh.load(source,force='scene',process=False);controls=NativeControls(scene,'negative_y',512)
trial=ROOT/'data/texture-engine-20261012/neural-hinata-trial1';references={}
for view in controls.views:
    rgb=np.asarray(Image.open(trial/'neural_views'/(view+'.png')).convert('RGB'));references[view]=np.dstack([rgb,np.uint8(controls.rasters[view][...,3]>.5)*255])
for resolution in [2048,4096]:
    directory=ROOT/'data/texture-engine-20261012'/f'hinata-cached-neural-{resolution}'
    report=texture_scene(scene,references,directory,{'provider':'neural_multiview','resolution':resolution,'uv_mode':'preserve','front_axis':'negative_y'},controls)
    report['view_source']='reused unchanged six real neural trial images; no repeated inference or claimed 4K native generation'
    report['neural']=json.loads((trial/'neural.json').read_text(encoding='utf-8'))
    (directory/'texture.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    (directory/'options.json').write_text(json.dumps({'front_axis':'negative_y','opposite_side':True,'render_resolution':512}),encoding='utf-8')
    print(json.dumps({'atlas':resolution,'seconds':report['seconds'],'coverage':report['synthesized_percent'],'geometry':report['geometry']['equivalent']}),flush=True)
