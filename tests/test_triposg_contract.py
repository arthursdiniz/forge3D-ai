import pytest
import json
from backend.schemas import GenerationOptions
from backend.quality_settings import generation_settings,validate_provider_options
from backend.providers import TripoSGProvider

def test_triposg_has_only_real_validated_profile_and_no_texture_controls():
    settings=generation_settings('balanced','triposg')
    assert settings['num_inference_steps']==50
    assert settings['hierarchical_octree_depth']==8
    assert settings['texture_method']=='none'
    assert settings['texture_resolution'] is None
    assert settings['auto_decimate'] is False
    with pytest.raises(ValueError):generation_settings('fast','triposg')

def test_triposg_quality_extracts_a_finer_field_without_automatic_decimation():
    settings=generation_settings('quality','triposg')
    assert settings['hierarchical_octree_depth']==9 and settings['mc_resolution']==512
    assert settings['auto_decimate'] is False and settings['texture_method']=='none'

def test_provider_specific_seed_and_texture_validation():
    validate_provider_options('triposg',GenerationOptions(seed=42))
    with pytest.raises(ValueError):validate_provider_options('triposr',GenerationOptions(seed=42))
    with pytest.raises(ValueError):validate_provider_options('triposg',GenerationOptions(texture_resolution=2048))
    with pytest.raises(ValueError):validate_provider_options('triposg',GenerationOptions(quality='fast'))

def test_triposg_rejects_occupancy_that_encoder_center_crop_would_clip():
    validate_provider_options('triposg',GenerationOptions(foreground_ratio=0.875))
    with pytest.raises(ValueError):validate_provider_options('triposg',GenerationOptions(foreground_ratio=0.95))
    validate_provider_options('triposr',GenerationOptions(foreground_ratio=0.95))

def test_triposg_health_requires_upstream_code_and_matching_proof(tmp_path):
    provider=TripoSGProvider(tmp_path)
    (tmp_path/'.venv-sg/Scripts').mkdir(parents=True)
    provider.python.touch()
    (tmp_path/'backend').mkdir();(tmp_path/'backend/inference_sg.py').touch()
    weights=tmp_path/'models/triposg';weights.mkdir(parents=True)
    (weights/'model_index.json').write_bytes(b'{}')
    manifest={'download_complete':True,'revision':'2c1c516d22d58db486a058d98d31bb6177344e06','files':[{'path':'model_index.json','bytes':2}]}
    (weights/'download_manifest.json').write_text(json.dumps(manifest))
    proof={'passed':True,'code_revision':'fc5c40990181e2a756c4e0b1c2f4d6b5202faf8c','weight_revision':manifest['revision'],'validated_profile':generation_settings('balanced','triposg')}
    (weights/'validation.json').write_text(json.dumps(proof))
    assert provider.health_check()['available'] is False # A venv and weights do not provide the upstream pipeline.
    vendor=tmp_path/'vendor/TripoSG/triposg'
    for path in ['pipelines/pipeline_triposg.py','models/autoencoders/autoencoder_kl_triposg.py','models/autoencoders/vae.py','models/transformers/triposg_transformer.py']:
        file=vendor/path;file.parent.mkdir(parents=True,exist_ok=True);file.touch()
    assert provider.health_check()['available'] is True
    proof['weight_revision']='outdated';(weights/'validation.json').write_text(json.dumps(proof))
    assert provider.health_check()['available'] is False
