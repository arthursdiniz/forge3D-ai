import json
from fastapi.testclient import TestClient
from backend.app import create_app


def test_hinata_comparison_exposes_both_sides_and_originals_without_fake_ratings(tmp_path):
    root=tmp_path/'character-advanced-20261011'
    proof=root/'validation-evidence';proof.mkdir(parents=True)
    directory=root/'advanced-validated-prototype/candidates/0';directory.mkdir(parents=True)
    (directory/'model.glb').write_bytes(b'preserved model')
    (directory/'source.png').write_bytes(b'reference')
    (directory/'inference.json').write_text(json.dumps({'seed':42,'seed_supported':True,'texture':{'method':'reference_visible_front'}}))
    for appearance in ['textured','clay']:
        (proof/'advanced42'/appearance).mkdir(parents=True)
        for view in ['front','side','side_opposite','rear','three_quarter']:
            (proof/'advanced42'/appearance/f'qa_{view}.png').write_bytes(b'real render fixture')
    (proof/'evidence.json').write_text(json.dumps({'passed':True,'variants':{'advanced42':{'integrity':[]}},'exports':{'advanced42':{'validation':{'passed':True}}}}))
    with TestClient(create_app(tmp_path,start_worker=False)) as client:
        result=client.get('/api/quality/comparison').json()
        case=next(case for case in result['cases'] if case['id']=='hinata')
        variant=case['variants'][0]
        assert variant['metadata']['seed']==42 and result['reviews']==[]
        assert 'side_opposite' in variant['renders']
        assert client.get(variant['renders']['side_opposite']).content==b'real render fixture'
        assert client.get(variant['model']).content==b'preserved model'
        assert client.get('/api/quality/character-files/validation-evidence/%2e%2e/%2e%2e/jobs.json').status_code==404
        response=client.post('/api/quality/reviews',json={'category':'hinata','variant':'advanced42','ratings':{'proportions':3},'notes':'Manual, not an AI score.'})
        assert response.status_code==200
        assert client.get('/api/quality/comparison').json()['reviews'][0]['assessment']=='manual'
