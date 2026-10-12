import pytest
from backend.schemas import GenerationOptions,Operation
from backend.quality_settings import validate_provider_options


def test_quality_mode_candidates_are_supported_without_changing_legacy_two():
    from backend.character_advanced import candidate_seeds
    assert candidate_seeds(42)==[42,43]
    assert candidate_seeds(4294967294,5)==[4294967294,4294967295,0,1,2]
    for count in [1,3,5]:
        validate_provider_options('hunyuan_mini',GenerationOptions(quality='quality',quality_mode=True,candidate_count=count))
        validate_provider_options('triposg',GenerationOptions(quality='balanced',quality_mode=True,candidate_count=count))
    with pytest.raises(ValueError):validate_provider_options('triposr',GenerationOptions(quality_mode=True,candidate_count=3))


def test_character_options_do_not_fake_semantic_conditioning_or_symmetry():
    options=GenerationOptions(character_mode=True,character_category='anime',analysis_id='a'*32)
    assert options.strategy=='generative'
    operation=Operation(operation='symmetry',symmetry_mode='soft',symmetry_regions=['torso'],symmetry_confirmed=True)
    assert operation.symmetry_strength<=.3
    with pytest.raises(ValueError):Operation(operation='symmetry',symmetry_mode='strong',symmetry_regions=[],symmetry_confirmed=False)


def test_game_ready_requires_budget_and_real_supported_bake_resolution():
    operation=Operation(operation='game_ready',target_triangles=10000,bake_normal=True,texture_resolution=2048)
    assert operation.target_triangles==10000
    with pytest.raises(ValueError):Operation(operation='game_ready',target_triangles=3)
