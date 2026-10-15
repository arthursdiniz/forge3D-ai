"""Real local reconstruction once, then postprocessing retry without another inference."""
import hashlib
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from fastapi.testclient import TestClient
from backend.app import create_app
from backend.worker import Worker

QA = ROOT / 'data/ux-upgrade-20261015'
folder = QA / 'model-checkpoint-flow'; assert not folder.exists()
reference = ROOT / 'data/test-inputs/hinata-shoyo-reference-20261011.png'
source_hash = hashlib.sha256(reference.read_bytes()).hexdigest()
app = create_app(folder, start_worker=False); client = TestClient(app); store = app.state.store
response = client.post('/api/workflows/model', data={'options': json.dumps({'category': 'anime', 'provider': 'hunyuan_mini', 'quality': 'balanced', 'seed': 42})}, files={'image': ('reference.png', reference.read_bytes(), 'image/png')})
assert response.status_code == 201, response.text
first = response.json(); worker = Worker(ROOT, store); actual_blender = worker.blender; actual_process = worker.run_process
calls = []
def tracked_process(command, *args, **kwargs):
    if any('inference_hy.py' in str(value) for value in command):
        calls.append('hunyuan-mini inference')
    return actual_process(command, *args, **kwargs)
worker.run_process = tracked_process
def deliberate_postprocessing_fault(*args, **kwargs):
    raise RuntimeError('QA deliberate postprocessing failure after actual neural reconstruction')
worker.blender = deliberate_postprocessing_fault
start = time.monotonic()
try:
    worker.process_job(first)
except RuntimeError as error:
    assert 'QA deliberate' in str(error), str(error)
    store.update(first['id'], status='failed', error=str(error))
else:
    raise AssertionError('Expected deliberate postprocessing fault')
first_seconds = time.monotonic() - start
stage = store.directory(first['id']) / 'inference-stage'
before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in stage.iterdir() if p.is_file()}
response = client.post('/api/workflows/' + first['id'] + '/retry'); assert response.status_code == 201, response.text
second = response.json(); worker.blender = actual_blender; start = time.monotonic(); worker.process_job(second)
retry_seconds = time.monotonic() - start
result = store.get(second['id']); assert result['status'] == 'completed'
assert result['metadata']['workflow']['inference_cache_reused'] is True
assert calls == ['hunyuan-mini inference'], calls
assert before == {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in stage.iterdir() if p.is_file()}
assert hashlib.sha256(reference.read_bytes()).hexdigest() == source_hash
assert store.get(first['id'])['status'] == 'failed'
report = {'passed': True, 'scope': 'Actual Hunyuan-mini inference once; deliberate Blender-stage failure, API retry, actual Blender postprocessing. No second inference.', 'first': first['id'], 'retry': second['id'], 'inference_calls': len(calls), 'first_wall_seconds': first_seconds, 'retry_wall_seconds': retry_seconds, 'checkpoint_unchanged': True, 'result': result}
(QA / 'model-checkpoint-validation.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('ACTUAL_MODEL_CHECKPOINT_RETRY_PASS ' + json.dumps({key: report[key] for key in ['inference_calls', 'first_wall_seconds', 'retry_wall_seconds']}), flush=True)
