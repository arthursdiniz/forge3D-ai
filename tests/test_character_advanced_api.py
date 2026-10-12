import io
import json
from PIL import Image
from fastapi.testclient import TestClient
from backend.app import create_app


def test_advanced_unmasked_projection_is_rejected_before_creating_job(tmp_path, monkeypatch):
    class ProvenProvider:
        def health_check(self):
            return {'available': True, 'presets': ['balanced', 'quality', 'advanced']}
    monkeypatch.setattr('backend.app.get_provider', lambda *args: ProvenProvider())
    image = io.BytesIO()
    Image.new('RGB', (64, 96), 'red').save(image, 'PNG')
    with TestClient(create_app(tmp_path, start_worker=False)) as client:
        for feature in [{'reference_texture': 'front'}, {'refine_reference': True}]:
            response = client.post('/api/jobs', files={'image': ('opaque.png', image.getvalue(), 'image/png')}, data={'provider': 'hunyuan_mini', 'options': json.dumps({'quality': 'advanced', 'background_mode': 'keep', **feature})})
            assert response.status_code == 422
            assert 'máscara' in response.json()['detail']
        assert client.get('/api/jobs').json() == []


def test_hunyuan_unproven_profile_is_rejected_before_creating_job(tmp_path, monkeypatch):
    class PartiallyProvenProvider:
        def health_check(self):
            return {'available': True, 'presets': ['balanced']}
    monkeypatch.setattr('backend.app.get_provider', lambda *args: PartiallyProvenProvider())
    image = io.BytesIO()
    Image.new('RGB', (64, 96), 'red').save(image, 'PNG')
    with TestClient(create_app(tmp_path, start_worker=False)) as client:
        response = client.post('/api/jobs', files={'image': ('opaque.png', image.getvalue(), 'image/png')}, data={'provider': 'hunyuan_mini', 'options': '{"quality":"advanced"}'})
        assert response.status_code == 422
        assert client.get('/api/jobs').json() == []


def test_original_stops_at_selected_candidate_generation_boundary(tmp_path):
    app=create_app(tmp_path,start_worker=False)
    store=app.state.store
    batch=store.create('Batch','hunyuan_mini',{'seed':42,'quality':'advanced'})
    candidate=store.create('Candidate2','hunyuan_mini',{'seed':43},parent=batch['id'])
    derived=store.create('Decimated2','hunyuan_mini',{},kind='transform',parent=candidate['id'])
    with TestClient(app) as client:
        for identifier in [candidate['id'],derived['id']]:
            original=client.get('/api/jobs/'+identifier+'/original').json()
            assert original['id']==candidate['id'] and original['options']['seed']==43
            assert original['parent']==batch['id']
