import pytest
from backend.quality_settings import generation_settings
from backend.hunyuan_mv_provider import validate_native_views

def test_multiview_profile_keeps_measured_memory_parameters():
    profile=generation_settings('balanced','hunyuan_mv')
    assert profile['mc_resolution']==256 and profile['num_inference_steps']==50
    assert profile['model_cpu_offload'] is False
    with pytest.raises(ValueError):generation_settings('quality','hunyuan_mv')

def test_native_views_are_named_distinct_views_without_collages():
    assert validate_native_views({'front':'f','left':'l','back':'b'})==['front','left','back']
    for refs in [{'front':'f'},{'front':'f','collage':'c'},{'left':'l','back':'b'}]:
        with pytest.raises(ValueError):validate_native_views(refs)
