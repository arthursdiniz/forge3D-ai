import io
import json
from PIL import Image
from fastapi.testclient import TestClient
from backend.app import create_app


def png(color):
    target=io.BytesIO();Image.new('RGBA',(64,96),color).save(target,'PNG');return target.getvalue()


def test_manual_review_is_persisted_without_relabeling_points_as_ai(tmp_path):
    app=create_app(tmp_path,start_worker=False)
    with TestClient(app) as client:
        response=client.post('/api/character/analyze',files={'image':('a.png',png('orange'),'image/png')},data={'category':'anime','manual_only':'true'})
        assert response.status_code==201
        analysis=response.json();identifier=analysis['id']
        payload={'category':'anime','pose':'a_pose','view':'front','landmarks':{'left_shoulder':{'x':.4,'y':.3,'visibility':1,'source':'mediapipe'}}}
        reviewed=client.put('/api/character/analyses/'+identifier,json=payload)
        assert reviewed.status_code==200
        point=reviewed.json()['landmarks']['left_shoulder']
        assert point['source']=='manual' and point['visibility'] is None
        assert reviewed.json()['reviewed']
        assert client.get('/api/character/files/'+identifier+'/detector_analysis.json').json()['landmarks']=={}
        assert client.get('/api/character/files/'+identifier+'/source_upload.bin').status_code==404


def test_generation_rejects_interpretation_of_a_different_image(tmp_path):
    with TestClient(create_app(tmp_path,start_worker=False)) as client:
        analysis=client.post('/api/character/analyze',files={'image':('a.png',png('red'),'image/png')},data={'manual_only':'true'}).json()
        client.put('/api/character/analyses/'+analysis['id'],json={'landmarks':{}})
        response=client.post('/api/jobs',files={'image':('b.png',png('blue'),'image/png')},data={'options':json.dumps({'character_mode':True,'analysis_id':analysis['id']})})
        assert response.status_code==422 and 'referência' in response.json()['detail']
        assert client.get('/api/jobs').json()==[]


def test_character_analysis_must_be_reviewed_before_generation(tmp_path):
    with TestClient(create_app(tmp_path,start_worker=False)) as client:
        image=png('red');analysis=client.post('/api/character/analyze',files={'image':('a.png',image,'image/png')},data={'manual_only':'true'}).json()
        response=client.post('/api/jobs',files={'image':('a.png',image,'image/png')},data={'options':json.dumps({'character_mode':True,'analysis_id':analysis['id']})})
        assert response.status_code==422 and 'Revise' in response.json()['detail']
