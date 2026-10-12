from pathlib import Path
import pytest
from PIL import Image

def test_existing_alpha_is_preserved_and_reported(tmp_path):
    from backend.preprocess import prepare_image
    source=tmp_path/'input.png'
    image=Image.new('RGBA',(300,300),(0,0,0,0))
    image.paste((250,40,20,255),(140,20,143,280))
    image.save(source)
    original=source.read_bytes()
    report=prepare_image(source,tmp_path/'prepared.png',foreground_ratio=0.85,background_mode='auto',preparation_preset='hard_surface')
    assert report['background_action']=='preserved_alpha'
    assert report['source_size']==[300,300]
    assert report['effective_size']==[512,512]
    assert source.read_bytes()==original
    assert (tmp_path/'prepared.png').exists()

def test_low_resolution_and_clipped_alpha_are_reported(tmp_path):
    from backend.preprocess import prepare_image
    source=tmp_path/'clipped.png'
    image=Image.new('RGBA',(64,64),(0,0,0,0))
    image.paste((10,30,90,255),(0,4,24,58))
    image.save(source)
    report=prepare_image(source,tmp_path/'prepared.png',background_mode='keep')
    assert 'low_resolution' in report['warning_codes']
    assert 'touches_border' in report['warning_codes']
    assert report['upscale_adds_detail'] is False

def test_generation_modes_change_supported_parameters():
    from backend.quality_settings import generation_settings
    fast=generation_settings('fast','triposr')
    balanced=generation_settings('balanced','triposr')
    quality=generation_settings('quality','triposr')
    assert fast['mc_resolution']<balanced['mc_resolution']<quality['mc_resolution']
    assert balanced['texture_method']=='neural_atlas'
    assert quality['auto_decimate'] is False
    assert generation_settings('high','triposr')==quality

def test_unavailable_provider_does_not_fallback_to_mock(tmp_path):
    from backend.providers import get_provider
    provider=get_provider('triposg',tmp_path)
    assert provider.health_check()['available'] is False
    with pytest.raises(ValueError):
        get_provider('pretend3d',tmp_path)
def test_auto_preserves_existing_alpha_even_when_corners_are_opaque(tmp_path):
    from PIL import Image
    from backend.preprocess import prepare_image
    source=tmp_path/'mask.png'
    image=Image.new('RGBA',(300,300),(255,0,0,255))
    image.putpixel((150,150),(0,0,0,0));image.save(source)
    report=prepare_image(source,tmp_path/'prepared.png',background_mode='auto',model_dir=tmp_path/'missing-model')
    assert report['has_existing_alpha'] is True
    assert report['background_action']=='preserved_alpha'
