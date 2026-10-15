import hashlib,json
import pytest
from fastapi.testclient import TestClient
from backend.app import create_app
from tests.test_hair_api import parent

@pytest.mark.parametrize('view',['front','back','left','right'])
def test_semantic_reference_upload_preserves_pixels_for_each_view(tmp_path,monkeypatch,view):
    import io
    from PIL import Image
    monkeypatch.setattr('backend.texture_engine.semantic_routes.semantic_status',lambda root:{'installed':True,'available':True})
    app=create_app(tmp_path,start_worker=False);base=parent(app);client=TestClient(app)
    image=Image.new('RGBA',(32,24),(25,70,120,190));payload=io.BytesIO();image.save(payload,format='PNG')
    response=client.post('/api/jobs/'+base['id']+'/semantic/analyze',data={'options':json.dumps({'views':{view:{'profile':'anime'}}})},files={view:('reference.png',payload.getvalue(),'image/png')})
    assert response.status_code==201,response.text
    job=response.json();assert job['status']=='queued' and job['parent']==base['id']
    with Image.open(app.state.store.directory(job['id'])/'views'/view/'source.png') as saved:
        assert saved.size==image.size and saved.convert('RGBA').tobytes()==image.tobytes()
    assert (app.state.store.directory(base['id'])/'model.glb').read_bytes()==b'unchanged original'

def test_semantic_invalid_uploaded_reference_returns_validation_error(tmp_path,monkeypatch):
    monkeypatch.setattr('backend.texture_engine.semantic_routes.semantic_status',lambda root:{'installed':True,'available':True})
    app=create_app(tmp_path,start_worker=False);base=parent(app)
    response=TestClient(app).post('/api/jobs/'+base['id']+'/semantic/analyze',data={'options':'{}'},files={'front':('broken.png',b'not an image','image/png')})
    assert response.status_code==422


def test_semantic_strokes_and_classes_reject_invalid_coordinates_and_fake_labels():
    from backend.texture_engine.semantic_contracts import SemanticAnalysisOptions,SemanticPaintOptions
    with pytest.raises(ValueError):SemanticAnalysisOptions(views={'front':{'source_strokes':[{'points':[[float('nan'),.5]],'radius':.02,'label':4}]}})
    with pytest.raises(ValueError):SemanticAnalysisOptions(views={'front':{'target_strokes':[{'points':[[.5,.5]],'radius':.02,'label':99}]}})
    with pytest.raises(ValueError):SemanticPaintOptions(analysis_id='a'*32,classes=['fake'],reviewed_alignment=True)
    with pytest.raises(ValueError):SemanticPaintOptions(analysis_id='a'*32,reviewed_alignment=False)


def test_registration_anchors_allow_a_separate_semantic_edit_polygon():
    from backend.texture_engine.semantic_contracts import Registration
    value=Registration(source_box=[.4,.1,.6,.3],target_box=[.4,.1,.6,.3],target_polygon=[[.2,0],[.8,0],[.8,.4],[.2,.4]])
    assert value.model_dump()['target_polygon'][0]==(.2,0)


def test_semantic_analysis_is_versioned_bound_to_original_and_cancel_safe(tmp_path,monkeypatch):
    monkeypatch.setattr('backend.texture_engine.semantic_routes.semantic_status',lambda root:{'installed':True,'available':True})
    app=create_app(tmp_path,start_worker=False);base=parent(app);client=TestClient(app)
    response=client.post('/api/jobs/'+base['id']+'/semantic/analyze',data={'options':'{}'})
    assert response.status_code==201,response.text
    child=response.json();assert child['kind']=='semantic_analysis' and child['parent']==base['id']
    context_file=app.state.store.directory(child['id'])/'character_context.json'
    assert context_file.is_file() and json.loads(context_file.read_text())['scope'].startswith('Suggestions')
    assert (app.state.store.directory(base['id'])/'model.glb').read_bytes()==b'unchanged original'
    client.post('/api/jobs/'+child['id']+'/cancel');app.state.store.update(child['id'],status='completed')
    assert app.state.store.get(child['id'])['status']=='cancelled'


def test_semantic_paint_rejects_another_mesh_or_camera(tmp_path,monkeypatch):
    monkeypatch.setattr('backend.texture_engine.semantic_routes.semantic_status',lambda root:{'installed':True,'available':True})
    app=create_app(tmp_path,start_worker=False);base=parent(app);other=parent(app);store=app.state.store;client=TestClient(app)
    analysis=store.create('sem','imported',{},kind='semantic_analysis',parent=base['id']);store.update(analysis['id'],status='completed',metadata={'semantic_analysis':{'status':'reviewable','source_sha256':hashlib.sha256(b'unchanged original').hexdigest(),'front_axis':'negative_y','views':{'front':{}}}})
    settings={'analysis_id':analysis['id'],'reviewed_alignment':True}
    assert client.post('/api/jobs/'+other['id']+'/semantic/paint',json=settings).status_code==409
    assert client.post('/api/jobs/'+base['id']+'/semantic/paint',json={**settings,'front_axis':'x'}).status_code==409
    response=client.post('/api/jobs/'+base['id']+'/semantic/paint',json=settings);assert response.status_code==201,response.text
    assert response.json()['options']['provider']=='semantic_reference'

def test_semantic_paint_rejects_changed_analysis_reference_before_queue(tmp_path,monkeypatch):
    monkeypatch.setattr('backend.texture_engine.semantic_routes.semantic_status',lambda root:{'installed':True,'available':True})
    app=create_app(tmp_path,start_worker=False);base=parent(app);store=app.state.store;client=TestClient(app)
    analysis=store.create('sem','imported',{},kind='semantic_analysis',parent=base['id']);folder=store.directory(analysis['id'])/'views/front';folder.mkdir(parents=True);(folder/'source.png').write_bytes(b'changed')
    report={'status':'reviewable','source_sha256':hashlib.sha256(b'unchanged original').hexdigest(),'front_axis':'negative_y','views':{'front':{'file_sha256':{'source.png':hashlib.sha256(b'original').hexdigest()}}}}
    store.update(analysis['id'],status='completed',metadata={'semantic_analysis':report})
    response=client.post('/api/jobs/'+base['id']+'/semantic/paint',json={'analysis_id':analysis['id'],'reviewed_alignment':True})
    assert response.status_code==409
