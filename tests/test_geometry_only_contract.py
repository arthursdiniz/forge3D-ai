from backend.schemas import GenerationOptions

def test_geometry_only_option_is_independent_and_legacy_is_default():
    assert GenerationOptions().texture_output=='legacy'
    options=GenerationOptions(texture_output='geometry_only',quality='quality')
    assert options.texture_output=='geometry_only' and options.quality=='quality'
