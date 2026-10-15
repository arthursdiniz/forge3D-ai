import io
import json
from PIL import Image
from fastapi.testclient import TestClient
from backend.app import create_app

def source(app):
    store=app.state.store;job=store.create('existing','hunyuan_mini',{});folder=store.directory(job['id']);(folder/'model.glb').write_bytes(b'original-model');Image.new('RGBA',(128,256),(200,80,20,255)).save(folder/'source.png')
    store.update(job['id'],status='completed',artifacts={'model':'/api/files/'+job['id']+'/model.glb'})
    return store.get(job['id'])

def test_region_refinement_requires_review_and_strict_bounded_masks(tmp_path,monkeypatch):
    monkeypatch.setattr('backend.texture_engine.region_routes.regional_ready',lambda root:True)
    app=create_app(tmp_path,start_worker=False);parent=source(app);client=TestClient(app)
    base={'source_box':[.2,.1,.8,.3],'target_box':[.4,.05,.6,.2],'reviewed_alignment':True}
    for change in [{'source_box':[0,0,float('nan'),1]},{'target_box':[.5,.5,.2,.2]},{'reviewed_alignment':False},{'provider':'neural_inpainting'},{'protected':[[[0,0],[1,0],[2,2]]]}]:
        response=client.post('/api/jobs/'+parent['id']+'/texture/refine',data={'options':json.dumps({**base,**change})})
        assert response.status_code==422,response.text
    response=client.post('/api/jobs/'+parent['id']+'/texture/refine',data={'options':json.dumps(base)})
    assert response.status_code==201,response.text
    job=response.json();assert job['kind']=='texture' and job['parent']==parent['id'] and job['options']['provider']=='reference_region'
    assert (app.state.store.directory(parent['id'])/'model.glb').read_bytes()==b'original-model'
    assert (app.state.store.directory(job['id'])/'references/front/source.png').is_file()
    client.post('/api/jobs/'+job['id']+'/cancel');app.state.store.update(job['id'],status='completed')
    assert app.state.store.get(job['id'])['status']=='cancelled'

def test_face_reference_chooses_original_largest_safe_ancestry(tmp_path):
    from backend.texture_engine.face_reference import best_reference
    app=create_app(tmp_path,start_worker=False);parent=source(app);child=app.state.store.create('texture','hunyuan_mini',{},kind='texture',parent=parent['id'])
    folder=app.state.store.directory(child['id']);(folder/'references/front').mkdir(parents=True);Image.new('RGBA',(64,64)).save(folder/'references/front/source.png')
    result=best_reference(app.state.store,child)
    assert result['asset']==parent['id'] and result['height']==256

def test_explicit_face_upload_is_preferred_over_larger_body_ancestor(tmp_path):
    from backend.texture_engine.face_reference import best_reference
    app=create_app(tmp_path,start_worker=False);parent=source(app);child=app.state.store.create('face','hunyuan_mini',{'provider':'reference_region'},kind='texture',parent=parent['id'])
    folder=app.state.store.directory(child['id']);(folder/'references/front').mkdir(parents=True);Image.new('RGBA',(64,64)).save(folder/'references/front/source.png')
    (folder/'texture_references.json').write_text(json.dumps({'views':{'front':{'path':'references/front/source.png','original':None,'explicit_regional_upload':True}}}))
    assert best_reference(app.state.store,child)['asset']==child['id']

def test_region_missing_reference_requires_upload_and_malformed_upload_is_rejected(tmp_path,monkeypatch):
    monkeypatch.setattr('backend.texture_engine.region_routes.regional_ready',lambda root:True)
    app=create_app(tmp_path,start_worker=False);parent=source(app);(app.state.store.directory(parent['id'])/'source.png').unlink();client=TestClient(app)
    options={'source_box':[0,0,1,1],'target_box':[.4,.1,.6,.2],'reviewed_alignment':True}
    response=client.post('/api/jobs/'+parent['id']+'/texture/refine',data={'options':json.dumps(options)})
    assert response.status_code==422
    response=client.post('/api/jobs/'+parent['id']+'/texture/refine',data={'options':json.dumps(options)},files={'reference':('x.png',b'invalid','image/png')})
    assert response.status_code==422

def test_region_context_paths_are_not_arbitrary_and_review_is_version_choice(tmp_path):
    app=create_app(tmp_path,start_worker=False);client=TestClient(app)
    assert client.get('/api/texture/regions/../files/context.json').status_code in [404,422]
    assert client.get('/api/texture/regions/'+'a'*32+'/files/secret.env').status_code==404
    parent=source(app)
    assert client.post('/api/jobs/'+parent['id']+'/texture/review',json={'decision':'approve'}).status_code==409

def test_character_intelligence_reuse_is_bound_to_the_same_original_reference(tmp_path):
    from backend.texture_engine.face_reference import character_context
    app=create_app(tmp_path,start_worker=False);job=source(app);folder=app.state.store.directory(job['id'])
    (folder/'character_interpretation.json').write_text(json.dumps({'source_upload_sha256':'correct','landmarks':{'left_eye':{'x':.4,'y':.2,'source':'manual','reviewed':True}},'regions':{'face':{'bounds':[.3,.1,.6,.3],'status':'user_defined'}}}))
    assert character_context(app.state.store,job,'wrong') is None
    assert character_context(app.state.store,job,'correct')['regions']['face']['status']=='user_defined'

def test_regional_marker_without_actual_geometry_export_evidence_is_unavailable(tmp_path):
    from backend.texture_engine.providers import regional_proof_valid
    folder=tmp_path/'models/texture';folder.mkdir(parents=True);(folder/'region_validation.json').write_text(json.dumps({'passed':True,'source_sha256':{}}))
    assert regional_proof_valid(tmp_path) is False

def test_character_suggestions_survive_png_reencoding_with_verified_pixels(tmp_path):
    import hashlib
    from backend.texture_engine.face_reference import character_context
    app=create_app(tmp_path,start_worker=False);job=source(app);folder=app.state.store.directory(job['id'])
    image=Image.open(folder/'source.png').convert('RGBA')
    record={'source_upload_sha256':'original-upload-bytes','effective_image_sha256':hashlib.sha256(image.tobytes()).hexdigest(),'image_size':list(image.size),'regions':{'face':{'bounds':[.3,.1,.6,.3],'status':'user_defined'}}}
    (folder/'character_interpretation.json').write_text(json.dumps(record))
    assert character_context(app.state.store,job,'different-normalized-png',image)['regions']['face']['status']=='user_defined'
    assert character_context(app.state.store,job,'different-normalized-png',Image.new('RGBA',image.size,'red')) is None
