import hashlib,json
from pathlib import Path
import numpy as np
import pytest
from PIL import Image

def test_hair_model_manifest_verifies_code_weights_and_bounded_paths(tmp_path):
    from backend.hair.resources import verify_resources
    model=tmp_path/'models/hair';model.mkdir(parents=True);code=tmp_path/'vendor/hair-test';code.mkdir(parents=True)
    weight=model/'tiny.pth';weight.write_bytes(b'local tensor state');source=code/'network.py';source.write_text('safe source')
    digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    manifest={'weights':[{'path':'tiny.pth','bytes':weight.stat().st_size,'sha256':digest(weight)}],'source_sha256':{'vendor/hair-test/network.py':digest(source)},'licenses':['MIT','Apache-2.0']}
    (model/'manifest.json').write_text(json.dumps(manifest));assert verify_resources(tmp_path)['ready']
    weight.write_bytes(b'corrupt');assert not verify_resources(tmp_path)['ready']
    manifest['source_sha256']={'../outside.py':'x'};(model/'manifest.json').write_text(json.dumps(manifest));assert not verify_resources(tmp_path)['ready']

def test_semantic_crop_is_square_without_distorting_coordinates_or_alpha():
    from backend.hair.inference import square_crop,restore_prediction,CLASS_NAMES
    image=Image.new('RGBA',(120,240),(200,40,20,255));crop,frame=square_crop(image,[.25,.1,.75,.6])
    assert crop.width==crop.height and frame['original_size']==[120,240]
    mask=restore_prediction(np.ones((512,512),np.float32),frame,image.size)
    assert mask.shape==(240,120) and mask[30,35]==1 and mask[200,100]==0
    assert CLASS_NAMES==['background','hair','eyes','mouth','face','skin','clothes']

def test_optional_hair_models_missing_returns_manual_fallback(tmp_path):
    from backend.hair.inference import infer_semantic
    report=infer_semantic(Image.new('RGBA',(64,64)),[.1,.1,.9,.9],tmp_path,'cpu')
    assert report['status']=='manual_required' and report['mask'] is None and not report['neural_validated']

def test_explicit_cpu_depth_preparation_never_selects_cuda(monkeypatch):
    import torch
    from backend.hair.inference import depth_tensor
    monkeypatch.setattr(torch.cuda,'is_available',lambda:(_ for _ in ()).throw(AssertionError('Implicit CUDA selection')))
    tensor=depth_tensor(np.full((92,128,3),128,np.uint8),Path(__file__).resolve().parents[1],torch,'cpu')
    assert tensor.device.type=='cpu' and tensor.shape[0:2]==(1,3)
    assert tensor.shape[2]%14==0 and tensor.shape[3]%14==0 and torch.isfinite(tensor).all()
