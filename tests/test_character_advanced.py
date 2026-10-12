import pytest
from pydantic import ValidationError
from backend.schemas import GenerationOptions
from backend.quality_settings import generation_settings,validate_provider_options

def test_hunyuan_advanced_uses_real_candidates_and_validated_memory_profile():
    settings=generation_settings('advanced','hunyuan_mini')
    assert settings['candidate_count']==2 and settings['mc_resolution']==384
    assert settings['num_inference_steps']==50 and settings['guidance_scale']==5
    assert settings['model_cpu_offload'] is False and settings['auto_decimate'] is False
    validate_provider_options('hunyuan_mini',GenerationOptions(quality='advanced',seed=42,reference_texture='front'))

def test_advanced_options_cannot_silently_leak_into_other_modes_or_providers():
    for provider,options in [('triposr',{'quality':'advanced'}),('triposg',{'quality':'advanced'}),('triposr',{'reference_texture':'front'}),('hunyuan_mini',{'quality':'balanced','refine_reference':True}),('hunyuan_mini',{'quality':'quality','reference_texture':'front'})]:
        with pytest.raises(ValueError):validate_provider_options(provider,GenerationOptions(**options))

def test_candidate_seed_wrap_is_deterministic_and_preserves_base_seed():
    from backend.character_advanced import candidate_seeds
    assert candidate_seeds(42)==[42,43]
    assert candidate_seeds(4294967295)==[4294967295,0]
    with pytest.raises(ValueError):candidate_seeds(-1)

def test_masked_original_can_be_saved_without_downsampling_for_native_encoder(tmp_path):
    from PIL import Image
    import numpy as np
    from backend.preprocess import prepare_image
    rgba=np.zeros((700,500,4),np.uint8);rgba[30:680,50:450]=[212,43,17,255]
    source=tmp_path/'source.png';Image.fromarray(rgba).save(source)
    prepare_image(source,tmp_path/'prepared.png',background_mode='preserve_alpha',save_masked_source=True)
    assert np.array_equal(np.asarray(Image.open(tmp_path/'prepared_masked.png')),rgba)

def test_geometry_only_batch_does_not_copy_final_model_onto_itself(tmp_path,monkeypatch):
    from backend.character_advanced import finalize_model
    model=tmp_path/'model.glb';model.write_bytes(b'original model bytes')
    monkeypatch.setattr('shutil.copy2',lambda *args:pytest.fail('Same model must not be copied onto itself.'))
    finalize_model(model,tmp_path)
    assert model.read_bytes()==b'original model bytes'
