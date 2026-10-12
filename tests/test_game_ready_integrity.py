import pytest


def test_reduction_with_new_holes_is_not_published_as_game_ready():
    from backend.game_ready_integrity import validate_reduction
    before={'boundary_edges':0,'nonmanifold_edges':0,'duplicate_faces':0,'inconsistent_winding_edges':0,'connected_components':1,'signed_volume':1.,'checks':{'intersections':{'selected_faces':0}}}
    with pytest.raises(ValueError,match='boundary_edges'):
        validate_reduction({'integrity':before},{'integrity':{**before,'boundary_edges':3}})
    with pytest.raises(ValueError,match='intersections'):
        validate_reduction({'integrity':before},{'integrity':{**before,'checks':{'intersections':{'selected_faces':2}}}})


def test_existing_open_surface_is_not_closed_automatically():
    from backend.game_ready_integrity import validate_reduction
    before={'boundary_edges':5,'nonmanifold_edges':0,'duplicate_faces':0,'inconsistent_winding_edges':0,'connected_components':1,'signed_volume':0.,'checks':{'intersections':{'selected_faces':0}}}
    assert validate_reduction({'integrity':before},{'integrity':before})['passed'] is True
