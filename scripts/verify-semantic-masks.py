"""Actual offline parser runs on three existing user references; no synthetic proof."""
import json,socket,sys
from pathlib import Path
from PIL import Image
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
def offline(*args,**kwargs):raise RuntimeError('Semantic validation is offline.')
socket.socket.connect=offline;socket.create_connection=offline
from backend.texture_engine.semantic_inference import segment_image
from backend.instance import InstanceLock
QA=ROOT/'data/semantic-upgrade-20261014';cases=[('A-kageyama','data/assets/323051d419ba4e47a4f421fd25e31d5f/references/front/source.png',None),('B-hinata','data/test-inputs/hinata-shoyo-reference-20261011.png',None),('C-stylized-naruto','data/assets/9ba485c257e94f6c991fe387545d9ec2/source.png',[.35,0,.66,.2])]
lock=InstanceLock(ROOT/'data/gpu.lock');lock.acquire();reports={}
try:
    for name,reference,crop in cases:
        folder=QA/'masks'/name;image=Image.open(ROOT/reference).convert('RGBA');image.save(folder/'source.png') if folder.exists() else None
        labels,origin,report=segment_image(image,ROOT,crop,'anime',folder);image.save(folder/'source.png')
        assert report['neural_executed'] or report['cached_neural_result'],report
        assert all(np.isin(labels,[0,1,2,3,4,5,6,7]).ravel()) and (labels==4).sum()>32
        _,_,cached=segment_image(image,ROOT,report['portrait_crop'],'anime',folder/'cached');assert cached['cache_reused'] and not cached['neural_executed']
        reports[name]={'reference':reference,'unique_classes':np.unique(labels).tolist(),'class_pixels':{str(i):int((labels==i).sum()) for i in np.unique(labels)},'seconds':report['seconds'],'neural':report['neural_resources'],'crop':report['portrait_crop'],'cache_reused':cached['cache_reused'],'scope':report['scope']};print(name,json.dumps(reports[name]),flush=True)
finally:lock.release()
(QA/'real-semantic-masks.json').write_text(json.dumps(reports,indent=2),encoding='utf-8')
