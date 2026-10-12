import io
import json
from pathlib import Path

import pytest
from PIL import Image
from fastapi.testclient import TestClient
from backend.app import create_app
from backend.storage import Store
from backend.worker import Worker


def image_bytes(mode='RGBA'):
    stream = io.BytesIO()
    Image.new(mode, (100, 200), 'white').save(stream, 'PNG')
    return stream.getvalue()


@pytest.mark.parametrize('extra', [False, True])
def test_crop_does_not_replace_optional_uploads(tmp_path, extra):
    app = create_app(tmp_path, start_worker=False)
    files = {'image': ('front.png', image_bytes(), 'image/png')}
    if extra:
        files['left'] = ('left.png', image_bytes(), 'image/png')
    with TestClient(app) as client:
        response = client.post('/api/jobs', files=files, data={'options': json.dumps({'crop': [.1, .2, .8, .9]})})
        assert response.status_code == 201
        directory = app.state.store.directory(response.json()['id'])
        manifest = json.loads((directory / 'references.json').read_text())
        assert set(manifest['views']) == ({'front', 'left'} if extra else {'front'})
        assert (directory / 'source_upload.bin').read_bytes() == image_bytes()


def test_asymmetric_crop_transforms_reviewed_regions_and_preserves_original():
    from backend.reference_coordinates import cropped_interpretation
    original = {'image_size': [100, 200], 'category': 'anime', 'pose': 'neutral', 'view': 'front', 'reviewed': True,
                'landmarks': {'left_wrist': {'x': .6, 'y': .5, 'source': 'manual', 'reviewed': True},
                              'right_wrist': {'x': .1, 'y': .2, 'source': 'manual', 'reviewed': True}},
                'regions': {'accessories': {'bounds': [.55, .3, .7, .6], 'source': 'manual'},
                            'hair': {'bounds': [0, 0, .1, .1], 'source': 'manual'}}}
    result = cropped_interpretation(original, [.2, .1, .8, .9])
    assert result['landmarks']['left_wrist']['x'] == pytest.approx(2/3)
    assert 'right_wrist' not in result['landmarks']
    assert result['regions']['accessories']['bounds'] == pytest.approx([7/12, .25, 5/6, .625])
    assert result['regions']['hair']['bounds'] is None
    assert result['image_size'] == [60, 160]
    assert original['image_size'] == [100, 200]
    assert original['regions']['accessories']['bounds'] == [.55, .3, .7, .6]
    assert result['reference_transform']['crop_pixels'] == [20, 20, 80, 180]


@pytest.mark.parametrize('operation', ['symmetry', 'sculpt_refine', 'analyze_character', 'project_texture'])
def test_selective_worker_publishes_current_mesh_report(tmp_path, monkeypatch, operation):
    store = Store(tmp_path / 'data')
    worker = Worker(tmp_path, store)
    parent = store.create('source', 'hunyuan_mini', {'character_category': 'anime'})
    source_dir = store.directory(parent['id'])
    (source_dir / 'model.glb').write_bytes(b'original')
    (source_dir / 'source.png').write_bytes(image_bytes())
    (source_dir / 'references.json').write_text(json.dumps({'views': {'front': {'path': str(source_dir / 'source.png')}}}))
    parent = store.update(parent['id'], status='completed', artifacts={'model': 'original-url'}, metadata={'triangles': 20, 'vertices': 12, 'dimensions': [1, 2, 1], 'materials': 1})
    job = store.create(operation, 'hunyuan_mini', {'operation': operation, 'symmetry_mode': 'off'}, kind='transform', parent=parent['id'])
    def process(command, directory, *args, **kwargs):
        (directory / 'model.glb').write_bytes(b'edited')
        if operation == 'project_texture': (directory / 'texture_projection.json').write_text('{"method":"reference_projection"}')
        else: (directory / 'geometry_operation.json').write_text('{"accepted":false}')
    def blender(source, directory, mode, options):
        assert mode == 'compare'
        report = {'before': {'triangles': 18}, 'after': {'triangles': 18, 'vertices': 12, 'dimensions': [1, 2, 1], 'materials': 1}, 'warnings': [], 'blender_version': 'test'}
        (directory / 'comparison_report.json').write_text(json.dumps(report))
        for view in ['front', 'side', 'rear', 'three_quarter']:
            (directory / ('qa_' + view + '.png')).write_bytes(image_bytes())
    def diagnose(directory, *args):
        (directory / 'character_quality.json').write_text('{"scope":"current mesh"}')
        return {'scope': 'current mesh'}
    monkeypatch.setattr(worker, 'run_process', process)
    monkeypatch.setattr(worker, 'blender', blender)
    monkeypatch.setattr(worker, 'diagnose_character', diagnose)
    worker.process_job(job)
    completed = store.get(job['id'])
    assert completed['status'] == 'completed'
    assert completed['metadata']['triangles'] == 18
    report = json.loads((store.directory(job['id']) / 'mesh_report.json').read_text())
    assert report['before']['triangles'] == 20
    assert completed['artifacts']['character_quality'].endswith('character_quality.json')


def test_effective_mask_manifest_is_independent_of_diagnostics(tmp_path):
    from backend.reference_coordinates import record_effective_reference
    source = tmp_path / 'source.png'
    source.write_bytes(image_bytes('RGB'))
    masked = tmp_path / 'prepared_masked.png'
    Image.new('RGBA', (60, 160), (50, 50, 50, 0)).save(masked)
    (tmp_path / 'references.json').write_text(json.dumps({'views': {'front': {'path': str(source)}}}))
    record_effective_reference(tmp_path, {'crop': [.2, .1, .8, .9]})
    front = json.loads((tmp_path / 'references.json').read_text())['views']['front']
    assert front['masked_path'] == str(masked.resolve())
    assert front['coordinate_space'] == 'effective cropped image before encoder framing'
    assert front['reference_transform']['crop_pixels'] == [20, 20, 80, 180]


@pytest.mark.parametrize('provider', ['hunyuan_mv', 'character_base_mesh'])
def test_unimplemented_texture_resolution_is_rejected(provider):
    from backend.schemas import GenerationOptions
    from backend.quality_settings import validate_provider_options
    options = GenerationOptions(texture_resolution=4096, character_mode=True, strategy='base_mesh',analysis_id='a'*32) if provider == 'character_base_mesh' else GenerationOptions(texture_resolution=4096)
    with pytest.raises(ValueError): validate_provider_options(provider, options)


def test_python_executable_is_not_complete_cpu_setup(tmp_path):
    from backend.cpu_environment import cpu_environment_ready
    executable = tmp_path / '.venv-character/Scripts/python.exe'
    executable.parent.mkdir(parents=True)
    executable.write_bytes(b'incomplete environment')
    assert cpu_environment_ready(tmp_path, 'character') is False


def test_reviewed_crop_is_bound_to_effective_coordinates_in_generation(tmp_path):
    app = create_app(tmp_path, start_worker=False)
    with TestClient(app) as client:
        analysis = client.post('/api/character/analyze', files={'image': ('front.png', image_bytes(), 'image/png')}, data={'manual_only': 'true'}).json()
        saved = client.put('/api/character/analyses/'+analysis['id'], json={'category':'anime', 'pose':'neutral', 'view':'front', 'regions':{'accessories':[.55,.3,.7,.6]},'landmarks':{}})
        assert saved.status_code == 200
        generated = client.post('/api/jobs', files={'image':('front.png',image_bytes(),'image/png')},data={'options':json.dumps({'character_mode':True,'analysis_id':analysis['id'],'crop':[.2,.1,.8,.9]})})
        assert generated.status_code == 201
        directory = app.state.store.directory(generated.json()['id'])
        original = json.loads((directory/'character_interpretation_original.json').read_text())
        effective = json.loads((directory/'character_interpretation.json').read_text())
        assert original['image_size'] == [100,200]
        assert effective['image_size'] == [60,160]
        assert effective['regions']['accessories']['bounds'] == pytest.approx([7/12,.25,5/6,.625])


def test_transform_timing_includes_blender_work_before_diagnostics(tmp_path,monkeypatch):
    from backend.progress import StageTimeline
    now=[10.]
    monkeypatch.setattr('backend.worker.StageTimeline',lambda:StageTimeline(clock=lambda:now[0]))
    store=Store(tmp_path/'data');parent=store.create('source','triposr',{})
    (store.directory(parent['id'])/'model.glb').write_bytes(b'source')
    store.update(parent['id'],status='completed',metadata={'triangles':20},artifacts={'model':'source.glb'})
    job=store.create('transform','triposr',{'operation':'triangulate'},kind='transform',parent=parent['id']);worker=Worker(tmp_path,store)
    def blender(source,directory,mode,options):
        now[0]+=30 if mode=='transform' else 2
        (directory/'model.glb').write_bytes(b'processed')
        (directory/'mesh_report.json').write_text(json.dumps({'before':{'triangles':20},'after':{'triangles':20},'warnings':[],'blender_version':'test'}))
        for view in ['front','side','rear','three_quarter']:(directory/('qa_'+view+'.png')).write_bytes(image_bytes())
    monkeypatch.setattr(worker,'blender',blender)
    worker.process_job(job)
    assert store.get(job['id'])['metadata']['timing']['elapsed_seconds']==32
