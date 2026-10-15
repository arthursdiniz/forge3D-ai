import importlib
import json
import socket
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image


def test_catalog_preserves_batch_but_resolves_each_candidates_own_original(tmp_path):
    from backend.storage import Store
    from backend.workflows.catalog import catalog
    store = Store(tmp_path)
    batch = store.create('Batch', 'triposr', {})
    first = store.create('Candidate 1', 'triposr', {}, parent=batch['id'])
    second = store.create('Candidate 2', 'triposr', {}, parent=batch['id'])
    changed = store.create('Second refined', 'triposr', {}, kind='transform', parent=second['id'])
    for job in [batch, first, second, changed]:
        store.update(job['id'], status='completed', artifacts={'model': '/fixture.glb'}, metadata={'candidate_index': 1} if job['id'] == second['id'] else {})
    groups = catalog(store)
    assert len(groups) == 1 and len(groups[0]['versions']) == 4
    version = next(v for v in groups[0]['versions'] if v['id'] == changed['id'])
    assert version['original_id'] == second['id']
    assert version['candidate_index'] == 1


def test_partial_automatic_view_rejection_is_visible_even_when_refinement_succeeds(tmp_path, monkeypatch):
    # Importing the standalone offline CLI must not change the test process networking.
    connect, connection = socket.socket.connect, socket.create_connection
    cli = importlib.import_module('backend.workflows.texture_cli')
    socket.socket.connect, socket.create_connection = connect, connection
    source = tmp_path / 'model.glb'; source.write_bytes(b'fixture')
    refs = tmp_path / 'refs'; refs.mkdir()
    for view in ['front', 'left']:
        Image.new('RGBA', (32, 32)).save(refs / (view + '.png'))
    out = tmp_path / 'out'; out.mkdir()
    monkeypatch.setattr('trimesh.load', lambda *a, **k: object())
    monkeypatch.setattr('backend.hair.resources.verify_resources', lambda *a: {'ready': True})
    monkeypatch.setattr('backend.texture_engine.region_camera.RegionCamera', lambda *a, **k: SimpleNamespace(image=np.zeros((32, 32, 4), dtype=np.uint8)))
    monkeypatch.setattr('backend.texture_engine.face_detection.detect_anime', lambda *a: {'faces': [{'box': [.2, .2, .8, .8]}]})
    monkeypatch.setattr('backend.texture_engine.semantic_inference.segment_image', lambda *a: (None, None, {'neural_executed': False, 'fixture': True}))
    gates = iter([{'accepted': True, 'registration': {}}, {'accepted': False, 'reason': 'ambiguous'}])
    monkeypatch.setattr('backend.workflows.alignment.automatic_registration', lambda *a: next(gates))
    monkeypatch.setattr('backend.texture_engine.semantic_analysis.analyze_semantics', lambda *a: {'status': 'reviewable', 'views': {'front': {'source': {}, 'target': {}}}})
    monkeypatch.setattr('backend.texture_engine.semantic_paint.paint_semantic', lambda *a, **k: {'geometry': {'equivalent': True}, 'semantic': {'metrics': {'front': {'before': {}, 'after': {}}}, 'changed_pixels': 10, 'protected_pixels_equal': True}})
    monkeypatch.setattr('backend.texture_engine.texture_metrics.candidate_improved', lambda *a: True)
    report = cli.refine(source, out, refs, 'negative_y', 'reference')
    assert report['accepted']
    assert any('left' in warning for warning in report['warnings']), report


@pytest.mark.parametrize('change', ['none', 'output', 'resource', 'source', 'options', 'code'])
def test_model_retry_reuses_only_intact_content_bound_inference(tmp_path, monkeypatch, change):
    from backend.app import create_app
    from backend.config import atomic_json
    from backend.worker import Worker
    root = tmp_path / 'project'; root.mkdir()
    code = root / 'backend/inference.py'; code.parent.mkdir(); code.write_text('v1')
    weight = root / 'models/triposr/model.ckpt'; weight.parent.mkdir(parents=True); weight.write_bytes(b'weights')
    app = create_app(tmp_path / 'data', start_worker=False); store = app.state.store
    job = store.create('Retry model', 'triposr', {'texture_output': 'geometry_only', 'quality': 'balanced'}, kind='model_workflow')
    directory = store.directory(job['id']); Image.new('RGB', (32, 32)).save(directory / 'source.png')
    workflow = {'domain': 'model', 'warnings': [], 'settings': {}, 'steps': []}
    atomic_json(directory / 'workflow.json', workflow); store.update(job['id'], metadata={'workflow': workflow})
    provider = SimpleNamespace(health_check=lambda: {'available': True, 'required_free_mb': 0}, command=lambda *a: ['fixture-provider'])
    monkeypatch.setattr('backend.worker.get_provider', lambda *a: provider)
    monkeypatch.setattr('backend.worker.gpu_health', lambda: {'total_mb': 8192, 'used_mb': 0})
    worker = Worker(root, store); calls = []
    def infer(command, folder, timeout, read_stages=False):
        calls.append('inference')
        import trimesh
        for name in ['original.glb', 'raw_generation.glb']:
            (folder / name).write_bytes(trimesh.creation.box().export(file_type='glb'))
        Image.new('RGBA', (32, 32)).save(folder / 'prepared.png')
        atomic_json(folder / 'preparation.json', {})
        atomic_json(folder / 'inference.json', {'effective_settings': {}, 'texture': {'method': 'none'}, 'render_front_axis': 'x'})
    worker.run_process = infer
    worker.blender = lambda *a: (_ for _ in ()).throw(RuntimeError('deliberate postprocessing failure'))
    with pytest.raises(RuntimeError, match='deliberate'):
        worker.process_job(job)
    store.update(job['id'], status='failed')
    if change == 'output':
        (directory / 'inference-stage/original.glb').write_bytes(b'corrupt')
    elif change == 'resource': weight.write_bytes(b'changed')
    elif change == 'source': Image.new('RGB', (32, 32), 'blue').save(directory / 'source.png')
    elif change == 'options': store.update(job['id'], options={**job['options'], 'seed': 99})
    elif change == 'code': code.write_text('v2')
    retry = TestClient(app).post('/api/workflows/' + job['id'] + '/retry')
    assert retry.status_code == 201, retry.text
    def blender(source, folder, mode, options):
        for name in ['model.glb', 'qa_front.png', 'qa_side.png', 'qa_rear.png', 'qa_three_quarter.png']:
            (folder / name).write_bytes(b'fixture inspected output')
        atomic_json(folder / 'mesh_report.json', {'before': {'triangles': 2}, 'after': {'triangles': 2}, 'warnings': [], 'blender_version': 'fixture'})
    worker.blender = blender; worker.process_job(retry.json())
    assert len(calls) == (1 if change == 'none' else 2)
    assert store.get(job['id'])['status'] == 'failed'
    result = store.get(retry.json()['id'])
    assert result['status'] == 'completed'
    assert result['metadata']['workflow']['inference_cache_reused'] is (change == 'none')
