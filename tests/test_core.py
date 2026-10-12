import io
import json
from pathlib import Path

import pytest
from PIL import Image

def image_bytes():
    data = io.BytesIO()
    Image.new('RGB', (128, 96), 'white').save(data, 'PNG')
    return data.getvalue()

def test_preprocess_preserves_source_and_centers_alpha(tmp_path):
    from backend.preprocess import prepare_image
    source = tmp_path / 'source.png'
    image = Image.new('RGBA', (100, 100), (0, 0, 0, 0))
    image.paste((255, 0, 0, 255), (10, 20, 40, 70))
    image.save(source)
    original = source.read_bytes()
    prepare_image(source, tmp_path / 'prepared.png', foreground_ratio=0.8)
    result = Image.open(tmp_path / 'prepared.png')
    assert result.size == (512, 512)
    assert result.getpixel((256, 256))[0] > 200
    assert source.read_bytes() == original

def test_upload_validation_and_job_persistence(tmp_path):
    from fastapi.testclient import TestClient
    from backend.app import create_app
    with TestClient(create_app(tmp_path, start_worker=False)) as client:
        bad = client.post('/api/jobs', files={'image':('bad.png', b'not an image','image/png')})
        assert bad.status_code == 400
        invalid = client.post('/api/jobs', files={'image':('ok.png',image_bytes(),'image/png')}, data={'options':json.dumps({'foreground_ratio':2})})
        assert invalid.status_code == 422
        good = client.post('/api/jobs', files={'image':('ok.png',image_bytes(),'image/png')})
        assert good.status_code == 201
        record = good.json()
        assert record['status'] == 'queued'
        assert client.get('/api/jobs').json()[0]['id'] == record['id']
        assert client.get(f"/api/files/{record['id']}/../../models/model.ckpt").status_code in (404,400)
    with TestClient(create_app(tmp_path, start_worker=False)) as client:
        assert client.get('/api/jobs').json()[0]['id'] == record['id']

def test_job_recovery_marks_interrupted_work_failed(tmp_path):
    from backend.storage import Store
    store = Store(tmp_path)
    job = store.create('chair', 'triposr', {})
    store.update(job['id'], status='generating')
    store.recover()
    assert store.get(job['id'])['status'] == 'failed'
    assert 'interromp' in store.get(job['id'])['error'].lower()

def test_numeric_operations_are_bounded():
    from backend.schemas import Operation
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        Operation(operation='decimate', ratio=0)
    with pytest.raises(ValidationError):
        Operation(operation='fix_scale', height=10001)
    with pytest.raises(ValidationError):
        Operation(operation='run_python')

def test_cancel_queued_job(tmp_path):
    from fastapi.testclient import TestClient
    from backend.app import create_app
    with TestClient(create_app(tmp_path, start_worker=False)) as client:
        job = client.post('/api/jobs',files={'image':('a.png',image_bytes(),'image/png')}).json()
        assert client.post(f"/api/jobs/{job['id']}/cancel").status_code == 200
        assert client.get(f"/api/jobs/{job['id']}").json()['status'] == 'cancelled'

def test_cancel_is_terminal_even_when_worker_finishes(tmp_path):
    from backend.storage import Store
    store = Store(tmp_path)
    job = store.create('a','triposr',{})
    store.update(job['id'],status='cancelled',stage='Cancelado')
    store.update(job['id'],status='completed',stage='Pronto')
    assert store.get(job['id'])['status'] == 'cancelled'

def test_worker_can_claim_oldest_job_outside_history_window(tmp_path):
    from backend.storage import Store
    store = Store(tmp_path)
    oldest = store.create('oldest','triposr',{})
    for index in range(201):
        newer=store.create(str(index),'triposr',{})
        store.update(newer['id'],status='completed')
    claimed=store.claim_next()
    assert claimed['id']==oldest['id']
    assert store.claim_next() is None

def test_unpublished_upload_cannot_be_claimed(tmp_path):
    from backend.storage import Store
    store=Store(tmp_path)
    job=store.create('upload','triposr',{},initial_status='uploading')
    assert store.claim_next() is None
    store.update(job['id'],status='queued')
    assert store.claim_next()['id']==job['id']

def test_cross_origin_write_is_rejected(tmp_path):
    from fastapi.testclient import TestClient
    from backend.app import create_app
    with TestClient(create_app(tmp_path,start_worker=False)) as client:
        response=client.post('/api/jobs',headers={'Origin':'https://example.com'},files={'image':('a.png',image_bytes(),'image/png')})
        assert response.status_code==403

def test_cancel_cannot_override_completed_job(tmp_path):
    from backend.storage import Store
    store=Store(tmp_path)
    job=store.create('done','triposr',{})
    store.update(job['id'],status='completed')
    with pytest.raises(ValueError):
        store.cancel(job['id'])
    assert store.get(job['id'])['status']=='completed'

def test_single_instance_lock_blocks_second_backend(tmp_path):
    from backend.instance import InstanceLock
    first=InstanceLock(tmp_path/'server.lock')
    second=InstanceLock(tmp_path/'server.lock')
    first.acquire()
    try:
        with pytest.raises(RuntimeError):
            second.acquire()
    finally:
        first.release()
    second.acquire()
    second.release()

def test_original_endpoint_resolves_parent_chain(tmp_path):
    from fastapi.testclient import TestClient
    from backend.app import create_app
    app=create_app(tmp_path,start_worker=False)
    original=app.state.store.create('first','triposr',{})
    child=app.state.store.create('edited','triposr',{},kind='transform',parent=original['id'])
    final=app.state.store.create('edited twice','triposr',{},kind='transform',parent=child['id'])
    with TestClient(app) as client:
        response=client.get('/api/jobs/'+final['id']+'/original')
        assert response.status_code==200
        assert response.json()['id']==original['id']
