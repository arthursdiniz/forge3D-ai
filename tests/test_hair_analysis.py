import json
import numpy as np
import pytest
import trimesh
from PIL import Image


@pytest.mark.parametrize('pixels',[0,16])
def test_weak_semantic_hair_requests_manual_review_with_saved_images(tmp_path,monkeypatch,pixels):
    from backend.hair.analysis import analyze_scene
    # Isolate the expensive neural stages; retain real camera, masks, scalp and report writes.
    def semantic(image,box,root):
        mask=np.zeros((image.height,image.width),bool);mask[10,20:20+pixels]=True
        return {'mask':mask,'classes':mask.astype('u1'),'resources':{'fixture':'weak learned response'}}
    monkeypatch.setattr('backend.hair.analysis.infer_semantic',semantic)
    monkeypatch.setattr('backend.hair.analysis.infer_depth',lambda *args:{'depth':None,'status':'fixture'})
    scene=trimesh.Scene(trimesh.creation.icosphere(subdivisions=1,radius=.15))
    options={'source_face':[.3,.3,.7,.7],'target_face':[.3,.3,.7,.7],'style':'realistic','front_axis':'negative_y'}
    report=analyze_scene(scene,Image.new('RGBA',(64,64),'orange'),tmp_path,options,tmp_path/'analysis','source-digest')
    assert report['status']=='manual_required' and report['reason']
    assert report['options']==options and report['source_sha256']=='source-digest'
    assert report['understanding']['reason'] and report['understanding']['tips']==[]
    folder=tmp_path/'analysis'
    for name in ['source.png','model_front.png','mask_overlay.png','hair_source_mask.png','hair_model_mask.png']:
        assert (folder/name).is_file()
    assert json.loads((folder/'hair_analysis.json').read_text())['status']=='manual_required'
