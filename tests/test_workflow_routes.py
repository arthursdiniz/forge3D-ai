import io
import json
from fastapi.testclient import TestClient
from PIL import Image
from backend.app import create_app


def png(color='orange'):
    buffer = io.BytesIO()
    Image.new('RGB', (48, 64), color).save(buffer, format='PNG')
    return buffer.getvalue()


def capabilities(monkeypatch):
    monkeypatch.setattr('backend.workflows.planner.provider_statuses', lambda root: [
        {'id': 'triposr', 'name': 'TripoSR', 'available': True, 'presets': ['fast', 'balanced', 'quality']},
        {'id': 'hunyuan_mini', 'name': 'Hunyuan', 'available': False, 'presets': []}])
    monkeypatch.setattr('backend.workflows.planner.texture_statuses', lambda root: [
        {'id': 'reference_projection', 'available': True},
        {'id': 'neural_multiview', 'available': True}])


def base_model(store):
    job = store.create('Personagem', 'imported', {}, kind='import')
    (store.directory(job['id']) / 'model.glb').write_bytes(b'original geometry')
    return store.update(job['id'], status='completed', artifacts={'model': '/original.glb'},
                        metadata={'render_front_axis': 'x'})


def test_model_workflow_is_geometry_only_and_deduplicates_upload(tmp_path, monkeypatch):
    capabilities(monkeypatch)
    app = create_app(tmp_path, start_worker=False)
    client = TestClient(app)
    settings = {'category': 'anime', 'quality': 'balanced', 'request_key': 'one-action-123'}
    def submit(body=png()):
        return client.post('/api/workflows/model', data={'options': json.dumps(settings)},
                           files={'image': ('character.png', body, 'image/png')})
    response = submit()
    assert response.status_code == 201, response.text
    job = response.json()
    assert job['kind'] == 'model_workflow'
    assert job['options']['texture_output'] == 'geometry_only'
    assert job['options']['preparation_preset'] == 'stylized_character'
    assert not job['options']['character_mode']
    assert submit().json()['id'] == job['id']
    assert submit(png('blue')).status_code == 409
    assert len(app.state.store.list()) == 1


def test_workflow_invalid_image_creates_no_jobs(tmp_path, monkeypatch):
    capabilities(monkeypatch)
    app = create_app(tmp_path, start_worker=False)
    response = TestClient(app).post('/api/workflows/model', data={'options': '{}'},
                                   files={'image': ('bad.png', b'bad', 'image/png')})
    assert response.status_code == 400
    assert not app.state.store.list()


def test_texture_single_job_accepts_four_real_views_and_opaque_images(tmp_path, monkeypatch):
    capabilities(monkeypatch)
    app = create_app(tmp_path, start_worker=False)
    parent = base_model(app.state.store)
    response = TestClient(app).post('/api/workflows/' + parent['id'] + '/texture',
        data={'options': json.dumps({'request_key': 'texture-request-123', 'use_saved_references': False})},
        files={view: (view + '.png', png(), 'image/png') for view in ['front', 'back', 'left', 'right']})
    assert response.status_code == 201, response.text
    job = response.json()
    assert job['kind'] == 'texture_workflow' and job['parent'] == parent['id']
    assert job['options']['background_mode'] == 'remove'
    assert job['options']['front_axis'] == 'x'
    manifest = json.loads((app.state.store.directory(job['id']) / 'texture_references.json').read_text())
    assert set(manifest['views']) == {'front', 'back', 'left', 'right'}
    assert (app.state.store.directory(parent['id']) / 'model.glb').read_bytes() == b'original geometry'


def test_retry_preserves_failed_job_and_cancel_is_terminal(tmp_path, monkeypatch):
    capabilities(monkeypatch)
    app = create_app(tmp_path, start_worker=False)
    client = TestClient(app)
    response = client.post('/api/workflows/model', data={'options': '{}'}, files={'image': ('a.png', png())})
    first = response.json()
    store = app.state.store
    store.update(first['id'], status='failed', error='Interrupted')
    retry = client.post('/api/workflows/' + first['id'] + '/retry')
    assert retry.status_code == 201, retry.text
    second = retry.json()
    assert second['id'] != first['id'] and second['status'] == 'queued'
    assert store.get(first['id'])['status'] == 'failed'
    assert (store.directory(second['id']) / 'source.png').is_file()
    client.post('/api/jobs/' + second['id'] + '/cancel')
    store.update(second['id'], status='completed')
    assert store.get(second['id'])['status'] == 'cancelled'


def test_catalog_groups_lineage_without_treating_analyses_as_assets(tmp_path, monkeypatch):
    capabilities(monkeypatch)
    app = create_app(tmp_path, start_worker=False)
    store = app.state.store
    parent = base_model(store)
    child = store.create('Textura', 'imported', {}, kind='texture', parent=parent['id'])
    store.update(child['id'], status='completed', artifacts={'model': '/child.glb'}, metadata={'materials': [{'images': ['base.png']}]})
    for i in range(205):
        store.create('Analysis', 'imported', {}, kind='semantic_analysis', parent=parent['id'])
    catalog = TestClient(app).get('/api/library').json()
    assert len(catalog) == 1
    assert catalog[0]['id'] == parent['id']
    assert len(catalog[0]['versions']) == 2
    assert catalog[0]['has_texture']


def test_texture_unavailable_or_incompatible_style_creates_no_version(tmp_path, monkeypatch):
    capabilities(monkeypatch)
    monkeypatch.setattr('backend.workflows.planner.texture_statuses', lambda root: [{'id': 'reference_projection', 'available': True}])
    app = create_app(tmp_path, start_worker=False)
    base = base_model(app.state.store)
    client = TestClient(app)
    for options, status in [({'goal': 'realistic'}, 422), ({'provider': 'neural_multiview'}, 409)]:
        result = client.post('/api/workflows/' + base['id'] + '/texture', data={'options': json.dumps(options)},
                             files={'front': ('a.png', png())})
        assert result.status_code == status, result.text
    assert len(app.state.store.list()) == 1


def test_retry_rebinds_reference_paths_and_repeated_retry_does_not_duplicate(tmp_path, monkeypatch):
    capabilities(monkeypatch)
    app = create_app(tmp_path, start_worker=False)
    client = TestClient(app)
    original = client.post('/api/workflows/model', files={'image': ('a.png', png())}).json()
    app.state.store.update(original['id'], status='failed')
    retry = client.post('/api/workflows/' + original['id'] + '/retry').json()
    references = json.loads((app.state.store.directory(retry['id']) / 'references.json').read_text())
    from pathlib import Path
    path = Path(references['views']['front']['path'])
    assert path.is_relative_to(app.state.store.directory(retry['id'])) and path.is_file()
    assert client.post('/api/workflows/' + original['id'] + '/retry').json()['id'] == retry['id']


def test_two_simultaneous_submissions_share_one_job(tmp_path, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    capabilities(monkeypatch)
    app = create_app(tmp_path, start_worker=False)
    with TestClient(app) as client:
        def submit(_):
            return client.post('/api/workflows/model', data={'options': json.dumps({'request_key': 'same-user-action'})},
                               files={'image': ('reference.png', png())})
        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(pool.map(submit, range(2)))
    assert [r.status_code for r in responses] == [201, 201]
    assert responses[0].json()['id'] == responses[1].json()['id']
    assert len(app.state.store.list()) == 1


def test_saved_reference_preview_follows_closest_version(tmp_path, monkeypatch):
    capabilities(monkeypatch)
    app = create_app(tmp_path, start_worker=False); store = app.state.store
    base = base_model(store)
    version = store.create('Textured', 'imported', {}, kind='texture', parent=base['id'])
    for job, color in [(base, 'red'), (version, 'blue')]:
        folder = store.directory(job['id']) / 'references/front'; folder.mkdir(parents=True)
        (folder / 'source.png').write_bytes(png(color))
    response = TestClient(app).get('/api/workflows/' + version['id'] + '/references')
    assert response.status_code == 200
    assert response.json()['front'] == '/api/files/' + version['id'] + '/references/front/source.png'
