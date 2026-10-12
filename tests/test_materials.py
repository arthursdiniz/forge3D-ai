from pathlib import Path
from backend.materials import texture_channels

def test_normal_map_cannot_be_published_as_albedo(tmp_path):
    for name in ['Normal_1024.png','BaseColor_1024.png']:(tmp_path/name).write_bytes(b'actual map file')
    channels=texture_channels(tmp_path)
    assert channels['base_color']=='Textures/BaseColor_1024.png'
    assert channels['normal']=='Textures/Normal_1024.png'
    assert channels['roughness'] is None and channels['metallic'] is None

def test_geometry_only_package_has_no_invented_maps(tmp_path):
    channels=texture_channels(tmp_path)
    assert all(value is None for value in channels.values())
