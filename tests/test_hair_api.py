import json
import pytest
from PIL import Image
from fastapi.testclient import TestClient
from backend.app import create_app

def parent(app):
    j=app.state.store.create('head','hunyuan_mini',{});d=app.state.store.directory(j['id']);(d/'model.glb').write_bytes(b'unchanged original');Image.new('RGBA',(128,128),'orange').save(d/'source.png');return app.state.store.update(j['id'],status='completed',artifacts={'model':'/api/files/'+j['id']+'/model.glb'})

def test_hair_contract_rejects_nan_unsafe_masks_and_unreviewed_geometry():
    from backend.hair.contracts import HairAnalysisOptions,HairRefineOptions
    for value in [{'source_face':[0,0,float('nan'),1]},{'head_box':[.5,.5,.2,.2]},{'hair_polygon':[[0,0],[1,0],[2,1]]},{'preset':'fake_method'}]:
        with pytest.raises(ValueError):HairAnalysisOptions(**value)
    with pytest.raises(ValueError):HairRefineOptions(analysis_id='a'*32)
    with pytest.raises(ValueError):HairRefineOptions(analysis_id='a'*32,reviewed=True,attributes={'volume':float('nan')})

def test_hair_analysis_is_a_serial_job_and_never_overwrites_parent(tmp_path,monkeypatch):
    monkeypatch.setattr('backend.hair.routes.verify_resources',lambda root:{'ready':True})
    app=create_app(tmp_path,start_worker=False);j=parent(app);client=TestClient(app)
    r=client.post('/api/jobs/'+j['id']+'/hair/analyze',data={'options':'{}'})
    assert r.status_code==201,r.text
    child=r.json();assert child['kind']=='hair_analysis' and child['parent']==j['id'] and child['status']=='queued'
    assert (app.state.store.directory(j['id'])/'model.glb').read_bytes()==b'unchanged original'
    client.post('/api/jobs/'+child['id']+'/cancel');app.state.store.update(child['id'],status='completed');assert app.state.store.get(child['id'])['status']=='cancelled'

def test_hair_refine_rejects_other_source_or_obsolete_axis_and_review_is_immutable(tmp_path,monkeypatch):
    import hashlib
    monkeypatch.setattr('backend.hair.routes.hair_status',lambda root:{'available':True})
    app=create_app(tmp_path,start_worker=False);j=parent(app);other=parent(app);store=app.state.store
    analysis=store.create('analysis','hunyuan_mini',{},kind='hair_analysis',parent=other['id']);store.update(analysis['id'],status='completed',metadata={'hair_analysis':{'source_sha256':'wrong','front_axis':'negative_y'}})
    client=TestClient(app);opts={'analysis_id':analysis['id'],'reviewed':True}
    assert client.post('/api/jobs/'+j['id']+'/hair/refine',json=opts).status_code==409
    store.update(analysis['id'],parent=j['id'],metadata={'hair_analysis':{'status':'reviewable','source_sha256':hashlib.sha256(b'unchanged original').hexdigest(),'front_axis':'negative_y'}})
    assert client.post('/api/jobs/'+j['id']+'/hair/refine',json={**opts,'front_axis':'x'}).status_code==409
    r=client.post('/api/jobs/'+j['id']+'/hair/refine',json=opts);assert r.status_code==201,r.text
    candidate=r.json();store.update(candidate['id'],status='completed',metadata={'hair':{'status':'reviewable_candidate'}})
    reject=client.post('/api/jobs/'+candidate['id']+'/hair/review',json={'decision':'reject'});assert reject.json()['selected']==j['id']
    approve=client.post('/api/jobs/'+candidate['id']+'/hair/review',json={'decision':'approve'});assert approve.json()['selected']==candidate['id']

def test_manual_analysis_and_cyclic_hair_ancestry_cannot_queue_geometry(tmp_path,monkeypatch):
    import hashlib
    monkeypatch.setattr('backend.hair.routes.hair_status',lambda root:{'available':True})
    app=create_app(tmp_path,start_worker=False);j=parent(app);store=app.state.store;client=TestClient(app)
    analysis=store.create('manual','imported',{},kind='hair_analysis',parent=j['id']);store.update(analysis['id'],status='completed',metadata={'hair_analysis':{'status':'manual_required','source_sha256':hashlib.sha256(b'unchanged original').hexdigest(),'front_axis':'negative_y'}})
    assert client.post('/api/jobs/'+j['id']+'/hair/refine',json={'analysis_id':analysis['id'],'reviewed':True}).status_code==409
    hair=store.create('cycle','imported',{},kind='hair',parent=j['id']);(store.directory(hair['id'])/'model.glb').write_bytes(b'original');store.update(hair['id'],status='completed',metadata={'hair':{'base_source_asset':hair['id']}})
    assert client.post('/api/jobs/'+hair['id']+'/hair/analyze',data={'options':'{}'}).status_code==409

def test_core_api_does_not_import_optional_hair_numerical_dependencies():
    import os,subprocess
    from pathlib import Path
    root=Path(__file__).resolve().parents[1];python=root/'.venv/Scripts/python.exe'
    if not python.is_file():pytest.skip('Local core runtime test requires the installed Windows API environment.')
    environment=dict(os.environ);environment.pop('PYTHONPATH',None)
    result=subprocess.run([str(python),'-c','from backend.app import create_app; create_app(start_worker=False); print("CORE_HAIR_OPTIONAL_IMPORT_PASS")'],cwd=root,env=environment,capture_output=True,text=True,timeout=20)
    assert result.returncode==0,result.stderr

def test_saved_analysis_reference_is_reused_without_switching_images(tmp_path,monkeypatch):
    import io
    monkeypatch.setattr('backend.hair.routes.verify_resources',lambda root:{'ready':True})
    app=create_app(tmp_path,start_worker=False);j=parent(app);other=parent(app);client=TestClient(app);buffer=io.BytesIO();Image.new('RGBA',(64,64),'purple').save(buffer,format='PNG')
    first=client.post('/api/jobs/'+j['id']+'/hair/analyze',files={'reference':('ref.png',buffer.getvalue(),'image/png')}).json();app.state.store.update(first['id'],status='completed')
    second=client.post('/api/jobs/'+j['id']+'/hair/analyze',data={'options':json.dumps({'reference_analysis_id':first['id']})})
    assert second.status_code==201,second.text
    with Image.open(app.state.store.directory(second.json()['id'])/'source.png') as image:assert image.getpixel((0,0))==(128,0,128,255)
    assert client.post('/api/jobs/'+other['id']+'/hair/analyze',data={'options':json.dumps({'reference_analysis_id':first['id']})}).status_code==409

@pytest.mark.parametrize('kind',['texture','transform'])
def test_derived_hair_versions_resolve_to_retained_original_before_analysis(tmp_path,monkeypatch,kind):
    import hashlib
    monkeypatch.setattr('backend.hair.routes.verify_resources',lambda root:{'ready':True})
    monkeypatch.setattr('backend.hair.routes.hair_status',lambda root:{'available':True})
    app=create_app(tmp_path,start_worker=False);base=parent(app);store=app.state.store;client=TestClient(app)
    hair=store.create('candidate','imported',{},kind='hair',parent=base['id'])
    derived=store.create('derived','imported',{},kind=kind,parent=hair['id'])
    (store.directory(derived['id'])/'model.glb').write_bytes(b'renamed hair geometry')
    store.update(derived['id'],status='completed',metadata={'hair':{'base_source_asset':base['id']}})
    response=client.post('/api/jobs/'+derived['id']+'/hair/analyze',data={'options':'{}'})
    assert response.status_code==201,response.text
    analysis=response.json();assert analysis['parent']==base['id']
    store.update(analysis['id'],status='completed',metadata={'hair_analysis':{'status':'reviewable','source_sha256':hashlib.sha256(b'unchanged original').hexdigest(),'front_axis':'negative_y'}})
    result=client.post('/api/jobs/'+derived['id']+'/hair/refine',json={'analysis_id':analysis['id'],'reviewed':True})
    assert result.status_code==201,result.text
    assert result.json()['parent']==base['id']
    assert (store.directory(derived['id'])/'model.glb').read_bytes()==b'renamed hair geometry'

@pytest.mark.parametrize('kind',['texture','transform'])
def test_derived_hair_without_retained_source_is_rejected_before_queue(tmp_path,monkeypatch,kind):
    monkeypatch.setattr('backend.hair.routes.verify_resources',lambda root:{'ready':True})
    app=create_app(tmp_path,start_worker=False);base=parent(app);store=app.state.store
    child=store.create('derived','imported',{},kind=kind,parent=base['id']);(store.directory(child['id'])/'model.glb').write_bytes(b'generated hair')
    store.update(child['id'],status='completed',metadata={'hair':{'status':'reviewable_candidate'}})
    response=TestClient(app).post('/api/jobs/'+child['id']+'/hair/analyze',data={'options':'{}'})
    assert response.status_code==409,response.text
