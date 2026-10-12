"""Ablation only: real TripoSG with DINO processor448. Not a UI capability."""
import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.instance import InstanceLock
from backend.triposg_runtime import TripoSGRuntime
original_load=TripoSGRuntime.load
def load_experimental(self,*args,**kwargs):
    pipe=original_load(self,*args,**kwargs)
    pipe.feature_extractor_dinov2.size={'shortest_edge':512}
    pipe.feature_extractor_dinov2.crop_size={'height':448,'width':448}
    return pipe
TripoSGRuntime.load=load_experimental
from backend.inference_sg import main
lock=InstanceLock(ROOT/'data/gpu.lock');lock.acquire()
try:main()
finally:lock.release()
output=Path(sys.argv[sys.argv.index('--output')+1])
for filename in ['inference.json','preparation.json']:
    path=output/filename;value=json.loads(path.read_text())
    preparation=value['image_preparation'] if filename=='inference.json' else value
    preparation['encoder_normalization']='EXPERIMENTAL ImageNet mean/std; resize512 crop448, training distribution differs from standard224'
    if filename=='inference.json':
        value['effective_settings']['encoder_resolution']=448
        value['experimental']=True
        value['warnings'].append('Encoder448 é ablação experimental; não foi declarado superior ou disponibilizado na UI.')
    path.write_text(json.dumps(value,indent=2),encoding='utf-8')
print('REAL_ENCODER448_ABLATION_COMPLETE',flush=True)
