import io
import json
import pytest
from PIL import Image
from fastapi.testclient import TestClient
from backend.app import create_app

def image_bytes():
    output=io.BytesIO();Image.new('RGB',(64,96),'red').save(output,'PNG');return output.getvalue()

def test_quality_options_preserve_mode_defaults_and_old_aliases(tmp_path):
    with TestClient(create_app(tmp_path,start_worker=False)) as client:
        for mode in ['fast','balanced','quality','draft','high']:
            response=client.post('/api/jobs',files={'image':('a.png',image_bytes(),'image/png')},data={'options':json.dumps({'quality':mode,'background_mode':'auto','preparation_preset':'hard_surface'})})
            assert response.status_code==201,response.text
            assert response.json()['options']['texture_resolution'] is None
        response=client.post('/api/jobs',files={'image':('a.png',image_bytes(),'image/png')},data={'options':json.dumps({'seed':42})})
        assert response.status_code==422 # TripoSR has no stochastic seed control.

def test_comparison_has_no_fake_scores_and_persists_manual_review(tmp_path):
    benchmark=tmp_path/'quality-upgrade'
    (benchmark/'baseline/prop').mkdir(parents=True)
    (benchmark/'baseline/prop/record.json').write_text(json.dumps({'generation':{'metadata':{'triangles':42}},'export':{'metadata':{}}}))
    with TestClient(create_app(tmp_path,start_worker=False)) as client:
        comparison=client.get('/api/quality/comparison')
        assert comparison.status_code==200
        assert comparison.json()['reviews']==[]
        payload={'category':'prop','variant':'baseline','ratings':{'fidelity':3,'silhouette':2},'notes':'Handle discontinuity.'}
        assert client.post('/api/quality/reviews',json=payload).status_code==200
        assert client.get('/api/quality/comparison').json()['reviews'][0]['ratings']==payload['ratings']
        payload['ratings']['fidelity']=6
        assert client.post('/api/quality/reviews',json=payload).status_code==422
        assert client.get('/api/quality/files/baseline-source/backend/worker.py').status_code==404
        assert client.get('/api/quality/files/baseline/prop/../../../models/model.ckpt').status_code==404
    with TestClient(create_app(tmp_path,start_worker=False)) as client:
        assert len(client.get('/api/quality/comparison').json()['reviews'])==1

def test_exif_orientation_is_preserved_in_effective_source(tmp_path):
    output=io.BytesIO();image=Image.new('RGB',(40,80),'orange')
    exif=image.getexif();exif[274]=6;image.save(output,'JPEG',exif=exif)
    app=create_app(tmp_path,start_worker=False)
    with TestClient(app) as client:
        response=client.post('/api/jobs',files={'image':('upright.jpg',output.getvalue(),'image/jpeg')})
        assert response.status_code==201
        source=app.state.store.directory(response.json()['id'])/'source.png'
        assert Image.open(source).size==(80,40)
