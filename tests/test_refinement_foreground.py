import json
import sys
import pytest
import trimesh
from PIL import Image

def test_a_kept_opaque_background_is_not_used_as_an_object_silhouette(tmp_path,monkeypatch):
    from backend.refine_mesh import main
    source=tmp_path/'source.png';Image.new('RGB',(64,64),'white').save(source)
    model=tmp_path/'input.glb';trimesh.creation.box().export(model)
    options=tmp_path/'options.json';options.write_text(json.dumps({'operation':'refine_silhouette'}))
    generation=tmp_path/'generation.json';generation.write_text(json.dumps({'background_mode':'keep'}))
    monkeypatch.setattr(sys,'argv',['refine_mesh','--input',str(model),'--output',str(tmp_path/'new'),'--options',str(options),'--source',str(source),'--generation-options',str(generation)])
    with pytest.raises(ValueError,match='máscara'):main()
    assert not (tmp_path/'new/model.glb').exists()
