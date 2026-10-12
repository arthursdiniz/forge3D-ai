import json
from pathlib import Path
from backend.quality_settings import generation_settings

def test_hunyuan_is_available_only_after_matching_local_proof(tmp_path):
    from backend.hunyuan_provider import HunyuanMiniProvider
    provider=HunyuanMiniProvider(tmp_path)
    for name in ['.venv-hy/Scripts/python.exe','backend/inference_hy.py','vendor/Hunyuan3D-2/hy3dgen/shapegen/pipelines.py']:
        file=tmp_path/name;file.parent.mkdir(parents=True,exist_ok=True);file.touch()
    weights=tmp_path/'models/hunyuan-mini';weights.mkdir(parents=True)
    (weights/'model.fp16.safetensors').write_bytes(b'test')
    manifest={'download_complete':True,'revision':'f90a0f7df7d5e6f71109cf333f6a95a0ae3194a6','code_revision':'f8db63096c8282cb27354314d896feba5ba6ff8a','files':[{'path':'model.fp16.safetensors','bytes':4}]}
    (weights/'download_manifest.json').write_text(json.dumps(manifest))
    assert provider.health_check()['available'] is False
    proof={'passed':True,'weight_revision':manifest['revision'],'code_revision':manifest['code_revision'],'profiles':{'balanced':generation_settings('balanced','hunyuan_mini')}}
    (weights/'validation.json').write_text(json.dumps(proof))
    assert provider.health_check()['available'] and provider.health_check()['presets']==['balanced']
    proof['profiles']['advanced']=generation_settings('advanced','hunyuan_mini')
    (weights/'validation.json').write_text(json.dumps(proof))
    assert provider.health_check()['presets']==['balanced','advanced']
    proof['weight_revision']='outdated';(weights/'validation.json').write_text(json.dumps(proof))
    assert not provider.health_check()['available']
