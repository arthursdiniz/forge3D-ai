import json
from pathlib import Path
from fastapi.testclient import TestClient
from backend.app import create_app

def test_texture_job_is_immutable_and_retains_geometry_license(tmp_path):
    app=create_app(tmp_path,start_worker=False);store=app.state.store
    parent=store.create('existing','hunyuan_mini',{});source=store.directory(parent['id'])/'model.glb';source.write_bytes(b'preserved')
    store.update(parent['id'],status='completed',artifacts={'model':'/api/files/'+parent['id']+'/model.glb'})
    from PIL import Image
    import io
    buffer=io.BytesIO();image=Image.new('RGBA',(32,32),(255,0,0,255));image.putpixel((0,0),(0,0,0,0));image.save(buffer,format='PNG')
    client=TestClient(app)
    response=client.post(f"/api/jobs/{parent['id']}/texture",data={'options':json.dumps({'resolution':1024})},files={'front':('reference.png',buffer.getvalue(),'image/png')})
    assert response.status_code==201,response.text
    child=response.json();assert child['kind']=='texture' and child['parent']==parent['id'] and child['provider']=='hunyuan_mini'
    assert child['id']!=parent['id'] and source.read_bytes()==b'preserved'
    assert client.get(f"/api/jobs/{child['id']}/original").json()['id']==parent['id']
    assert client.post(f"/api/jobs/{child['id']}/cancel").status_code==200
    store.update(child['id'],status='completed');assert store.get(child['id'])['status']=='cancelled'

def test_safe_model_import_rejects_paths_and_untrusted_gltf_resources(tmp_path):
    client=TestClient(create_app(tmp_path,start_worker=False))
    for name,body in [('bad.gltf',json.dumps({'asset':{'version':'2.0'},'buffers':[{'uri':'C:/private.bin'}]}).encode()),('../bad.obj',b'v 0 0 0'),('skin.gltf',json.dumps({'asset':{'version':'2.0'},'skins':[{}]}).encode())]:
        response=client.post('/api/models/import',files={'model':(name,body,'application/octet-stream')})
        assert response.status_code==422,response.text
    response=client.post('/api/models/import',files={'model':('triangle.obj',b'v 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3','application/octet-stream')})
    assert response.status_code==201,response.text
    assert response.json()['kind']=='import' and response.json()['provider']=='imported'

def test_import_rejects_unsupported_uv_sets_and_invalid_json_structure(tmp_path):
    client=TestClient(create_app(tmp_path,start_worker=False))
    for document in [[],{'asset':{'version':'2.0'},'meshes':[{'primitives':[{'attributes':{'TEXCOORD_1':0}}]}]}, {'asset':{'version':'2.0'},'extensionsUsed':['KHR_texture_transform']}]:
        response=client.post('/api/models/import',files={'model':('unsupported.gltf',json.dumps(document).encode(),'model/gltf+json')})
        assert response.status_code==422,response.text

def test_unvalidated_neural_provider_is_explicitly_blocked(tmp_path,monkeypatch):
    from backend.texture_engine.providers import provider_statuses
    monkeypatch.setattr('backend.texture_engine.routes.provider_statuses',lambda root:provider_statuses(tmp_path))
    app=create_app(tmp_path,start_worker=False);store=app.state.store;parent=store.create('old','triposr',{})
    store.update(parent['id'],status='completed');(store.directory(parent['id'])/'model.glb').write_bytes(b'model')
    client=TestClient(app);health=client.get('/api/texture/providers')
    assert health.status_code==200
    assert next(item for item in health.json() if item['id']=='advanced_pbr')['available'] is False
    response=client.post(f"/api/jobs/{parent['id']}/texture",data={'options':json.dumps({'provider':'neural_multiview','conditioning':'text','prompt':'red ceramic'})})
    assert response.status_code==409,response.text
