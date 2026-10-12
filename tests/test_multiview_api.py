import hashlib,io,json
from PIL import Image
from fastapi.testclient import TestClient
from backend.app import create_app

def png(color):
    target=io.BytesIO();Image.new('RGBA',(64,96),color).save(target,'PNG');return target.getvalue()

class AvailableMV:
    def health_check(self):return {'available':True,'presets':['balanced'],'validated_view_counts':[2,3,4]}

def test_native_multiview_rejects_front_only_before_creating_a_job(tmp_path,monkeypatch):
    monkeypatch.setattr('backend.app.get_provider',lambda *args:AvailableMV())
    with TestClient(create_app(tmp_path,start_worker=False)) as client:
        result=client.post('/api/jobs',files={'image':('front.png',png('red'),'image/png')},data={'provider':'hunyuan_mv'})
        assert result.status_code==422
        assert client.get('/api/jobs').json()==[]

def test_all_named_inputs_are_preserved_and_hashed_and_only_native_model_conditions_them(tmp_path,monkeypatch):
    monkeypatch.setattr('backend.app.get_provider',lambda *args:AvailableMV())
    contents={'image':png('red'),'left':png('green'),'back':png('blue')}
    with TestClient(create_app(tmp_path,start_worker=False)) as client:
        result=client.post('/api/jobs',files={key:(key+'.png',value,'image/png') for key,value in contents.items()},data={'provider':'hunyuan_mv'})
        assert result.status_code==201
        job=result.json();manifest=client.get('/api/files/'+job['id']+'/references.json').json()
        assert manifest['conditioning']=='native_multiview'
        assert set(manifest['views'])=={'front','left','back'}
        for name,item in manifest['views'].items():
            content=contents['image' if name=='front' else name]
            assert item['sha256']==hashlib.sha256(content).hexdigest()
            assert (tmp_path/'assets'/job['id']/'references'/name/'source_upload.bin').read_bytes()==content

def test_invalid_extra_reference_cannot_leave_partial_upload(tmp_path,monkeypatch):
    monkeypatch.setattr('backend.app.get_provider',lambda *args:AvailableMV())
    with TestClient(create_app(tmp_path,start_worker=False)) as client:
        result=client.post('/api/jobs',files={'image':('front.png',png('red'),'image/png'),'left':('bad.png',b'bad','image/png')},data={'provider':'hunyuan_mv'})
        assert result.status_code==400
        assert client.get('/api/jobs').json()==[]
