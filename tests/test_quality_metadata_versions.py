from backend.worker import version_metadata

def test_derived_geometry_does_not_present_parent_character_measurements_as_current():
    original={'character_quality':{'silhouettes':{'front':{'iou':.9}}},'seed':44}
    derived=version_metadata(original,'transform')
    assert 'character_quality' not in derived
    assert original['character_quality']['silhouettes']['front']['iou']==.9
    assert derived['seed']==44
