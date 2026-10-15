"""Real sequential neural probes, offline GPU lock; original images unchanged."""
import json,socket,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
def blocked(*args,**kwargs):raise RuntimeError('Hair inference is offline.')
socket.socket.connect=blocked;socket.create_connection=blocked
from backend.instance import InstanceLock
from backend.hair.inference import infer_semantic,infer_depth
from PIL import Image
import numpy as np
qa=ROOT/'data/hair-upgrade-20261013/neural-probe';qa.mkdir(exist_ok=False);lock=InstanceLock(ROOT/'data/gpu.lock');lock.acquire()
try:
    for name,path,box in [('reference',ROOT/'data/test-inputs/hinata-shoyo-reference-20261011.png',[.28,0,.70,.23]),('model',ROOT/'data/texture-fidelity-20261013/hinata-regional-final-footprint/region_after_full.png',[.35,.04,.63,.25])]:
        image=Image.open(path).convert('RGBA');folder=qa/name;folder.mkdir();semantic=infer_semantic(image,box,ROOT,'cuda');assert semantic['neural_validated'] and semantic['mask'].any()
        for key in ['mask','face_mask']:Image.fromarray(semantic[key].astype('u1')*255).save(folder/(key+'.png'))
        Image.fromarray(semantic['classes']).save(folder/'classes.png');Image.fromarray(np.rint(semantic['hair_probability']*255).astype('u1')).save(folder/'hair_response.png')
        semantic={k:v for k,v in semantic.items() if not isinstance(v,np.ndarray)}
        depth=infer_depth(image,box,ROOT,'cuda');assert depth['neural_validated'] and np.isfinite(depth['depth']).all();values=depth.pop('depth');np.save(folder/'relative_depth.npy',values)
        foreground=values>0;low,high=np.percentile(values[foreground],[2,98]);visual=np.zeros_like(values,dtype='u1');visual[foreground]=np.clip((values[foreground]-low)/max(high-low,1e-6)*255,0,255).astype('u1');Image.fromarray(visual).save(folder/'relative_depth.png')
        report={'semantic':semantic,'depth':depth,'mask_pixels':int((np.asarray(Image.open(folder/'mask.png'))>0).sum()),'ground_truth_accuracy':None};(folder/'result.json').write_text(json.dumps(report,indent=2));print(name,json.dumps(report),flush=True)
finally:lock.release()
