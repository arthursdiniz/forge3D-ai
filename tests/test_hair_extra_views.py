import numpy as np
import trimesh
from PIL import Image
from tests.test_hair_understanding import mask_image

def test_only_registered_real_extra_views_contribute_guides(tmp_path,monkeypatch):
    from backend.hair.extra_views import extra_views
    for view in ['side','back']:Image.new('RGBA',(128,128),'orange').save(tmp_path/f'reference_{view}.png')
    monkeypatch.setattr('backend.hair.extra_views.infer_semantic',lambda *a:{'mask':mask_image(),'resources':{'test_fixture_not_neural':True}})
    monkeypatch.setattr('backend.hair.extra_views.infer_depth',lambda *a:{'depth':np.ones((128,128)),'test_fixture_not_neural':True})
    scalp={'center':[0,.7,0],'radii':[.14,.18,.13]};scene=trimesh.Scene(trimesh.creation.icosphere(radius=.15).apply_translation([0,.7,0]))
    tips,records=extra_views(scene,scalp,tmp_path,{'extra_scalp_boxes':{'back':[.3,.32,.72,.78]}},tmp_path)
    assert records[0]['status']=='manual_registration_required' and not records[0]['used_for_geometry']
    assert records[1]['used_for_geometry'] and tips and all(t['zone']=='back' and t['tip_world'][2]<0 for t in tips)
    assert 'real back' in tips[0]['observation'] and (tmp_path/'hair_back_mask.png').is_file()
