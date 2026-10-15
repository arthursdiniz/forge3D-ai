import hashlib
import json
import numpy as np
from backend.workflows.jobs import cache_key, reusable_stage
from backend.workflows.alignment import automatic_registration


def face(dx=0, deform=False):
    points = [{'index': i, 'x': .4 + (i % 6) * .035 + dx, 'y': .2 + (i // 6) * .035,
               'raw_score': .95, 'reviewed': False} for i in range(24)]
    if deform:
        points[4]['x'] += .3
    return {'box': [.35 + dx, .15, .65 + dx, .4], 'landmarks': points, 'raw_detection_score': .98}


def test_automatic_alignment_rejects_ambiguous_or_deformed_faces_without_human_review():
    accepted = automatic_registration([face()], [face(.02)])
    assert accepted['accepted'] and accepted['method'] == 'automatic_landmark_gate'
    assert not accepted['human_reviewed']
    assert not automatic_registration([face(), face(.2)], [face()])['accepted']
    assert not automatic_registration([face()], [face(deform=True)])['accepted']
    assert not automatic_registration([], [face()])['accepted']


def test_cache_is_bound_to_all_inputs_and_verified_output_bytes(tmp_path):
    root = tmp_path / 'project'; (root / 'backend').mkdir(parents=True)
    (root / 'backend' / 'pipeline.py').write_text('one')
    folder = tmp_path / 'stage'; folder.mkdir()
    (folder / 'model.glb').write_bytes(b'validated')
    (folder / 'texture.json').write_text('{"geometry":{"equivalent":true}}')
    inputs = {'source': 'abc', 'references': {'front': 'def'}, 'options': {'resolution': 1024}}
    key = cache_key(root, inputs)
    manifest = {'key': key, 'files': {name: hashlib.sha256((folder / name).read_bytes()).hexdigest()
                                    for name in ['model.glb', 'texture.json']}}
    (folder / 'stage-cache.json').write_text(json.dumps(manifest))
    assert reusable_stage(folder, key)
    assert not reusable_stage(folder, cache_key(root, {**inputs, 'source': 'changed'}))
    (root / 'backend' / 'pipeline.py').write_text('two')
    assert not reusable_stage(folder, cache_key(root, inputs))
    (folder / 'model.glb').write_bytes(b'corrupt')
    assert not reusable_stage(folder, key)


def test_cache_rejects_a_stage_without_a_passing_identity_report(tmp_path):
    folder = tmp_path / 'stage'; folder.mkdir()
    (folder / 'model.glb').write_bytes(b'output')
    (folder / 'texture.json').write_text('{"geometry":{"equivalent":false}}')
    (folder / 'stage-cache.json').write_text(json.dumps({'key': 'key', 'files': {
        name: hashlib.sha256((folder / name).read_bytes()).hexdigest() for name in ['model.glb', 'texture.json']}}))
    assert not reusable_stage(folder, 'key')


def test_automatic_evidence_cannot_authorize_a_different_registration():
    import pytest
    from backend.workflows.alignment import validate_automatic_evidence
    gate = automatic_registration([face()], [face(.02)])
    analysis = {'views': {'front': {'registration': gate['registration']}}}
    evidence = {'method': 'automatic_landmark_gate', 'human_reviewed': False,
                'views': {'front': {'source_faces': [face()], 'target_faces': [face(.02)]}}}
    validate_automatic_evidence(analysis, evidence)
    analysis['views']['front']['registration'] = {**gate['registration'], 'accept_unknown_target': True}
    with pytest.raises(ValueError):
        validate_automatic_evidence(analysis, evidence)


def test_automatic_evidence_covers_every_view_that_will_be_painted():
    import pytest
    from backend.workflows.alignment import validate_automatic_evidence
    gate = automatic_registration([face()], [face(.02)])
    analysis = {'views': {name: {'registration': gate['registration']} for name in ['front', 'back']}}
    evidence = {'method': 'automatic_landmark_gate', 'human_reviewed': False,
                'views': {'front': {'source_faces': [face()], 'target_faces': [face(.02)]}}}
    with pytest.raises(ValueError):
        validate_automatic_evidence(analysis, evidence)


def test_texture_workflow_publishes_once_after_render_and_preserves_failed_base_for_retry(tmp_path, monkeypatch):
    from backend.storage import Store
    from backend.worker import Worker
    from backend.config import atomic_json
    from backend.texture_engine.providers import TextureProvider
    store = Store(tmp_path / 'data'); root = tmp_path / 'project'; root.mkdir()
    parent = store.create('Base', 'imported', {}, kind='import')
    source = store.directory(parent['id']) / 'model.glb'; source.write_bytes(b'original')
    parent = store.update(parent['id'], status='completed', metadata={'render_front_axis': 'negative_y'}, artifacts={'model': '/original'})
    job = store.create('New texture', 'imported', {'provider': 'reference_projection', 'front_axis': 'negative_y'}, kind='texture_workflow', parent=parent['id'])
    folder = store.directory(job['id']); refs = folder / 'references/front'; refs.mkdir(parents=True); (refs / 'source.png').write_bytes(b'pixels')
    atomic_json(folder / 'texture_references.json', {'views': {'front': {'path': 'references/front/source.png'}}})
    atomic_json(folder / 'workflow.json', {'source_sha256': hashlib.sha256(b'original').hexdigest(), 'settings': {'goal': 'reference'}, 'warnings': [], 'steps': []})
    monkeypatch.setattr(TextureProvider, 'preflight', lambda self, opts: None)
    monkeypatch.setattr(TextureProvider, 'command', lambda *args: ['real-child-contract'])
    worker = Worker(root, store); calls = []
    def subprocess(command, directory, timeout, read_stages=False):
        assert store.get(job['id'])['status'] != 'completed'
        calls.append('base')
        (directory / 'model.glb').write_bytes(b'textured same geometry fixture')
        maps = directory / 'textures/000'; maps.mkdir(parents=True); (maps / 'Albedo.png').write_bytes(b'albedo')
        atomic_json(directory / 'texture.json', {'provider': 'reference_projection', 'geometry': {'equivalent': True},
            'materials': [{'geometry': 'mesh', 'maps': {'albedo': 'textures/000/Albedo.png'}}]})
    def blender(source, directory, mode, options):
        assert calls == ['base'] and store.get(job['id'])['status'] != 'completed'
        calls.append('inspection')
        atomic_json(directory / 'comparison_report.json', {'after': {'triangles': 2}, 'warnings': [], 'blender_version': 'fixture'})
        for view in ['front', 'side', 'side_opposite', 'rear', 'three_quarter']:
            (directory / ('qa_' + view + '.png')).write_bytes(b'render fixture')
    worker.run_process = subprocess; worker.blender = blender
    worker.process_job(job)
    result = store.get(job['id'])
    assert calls == ['base', 'inspection'] and result['status'] == 'completed'
    assert result['metadata']['workflow']['result'] == 'qualified'
    assert (folder / 'base/stage-cache.json').is_file()
    assert source.read_bytes() == b'original'
