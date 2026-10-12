import pytest
from backend.schemas import Operation
from pydantic import ValidationError

def test_refinement_and_cleanup_limits_are_validated():
    assert Operation(operation='refine_silhouette').refinement_strength==0.65
    assert Operation(operation='cleanup').max_fragment_faces==32
    for values in [{'operation':'refine_silhouette','max_displacement_ratio':0.031},{'operation':'refine_silhouette','refinement_strength':2},{'operation':'cleanup','max_fragment_faces':33},{'operation':'cleanup','max_fragment_extent':0.007}]:
        with pytest.raises(ValidationError):Operation(**values)

def test_silhouette_operation_requires_provider_with_known_reference_orientation(tmp_path):
    from fastapi.testclient import TestClient
    from backend.app import create_app
    app=create_app(tmp_path,start_worker=False)
    a=app.state.store.create('SR','triposr',{});app.state.store.update(a['id'],status='completed',artifacts={'model':'example.glb'})
    b=app.state.store.create('SG','triposg',{});app.state.store.update(b['id'],status='completed',artifacts={'model':'example.glb'})
    with TestClient(app) as client:
        assert client.post('/api/jobs/'+a['id']+'/operations',json={'operation':'refine_silhouette'}).status_code==422
        response=client.post('/api/jobs/'+b['id']+'/operations',json={'operation':'refine_silhouette'})
        assert response.status_code==201 and response.json()['parent']==b['id']

def test_refinement_rejects_unmasked_reference_before_queuing(tmp_path):
    from fastapi.testclient import TestClient
    from backend.app import create_app
    app=create_app(tmp_path,start_worker=False)
    job=app.state.store.create('SG kept','triposg',{})
    app.state.store.update(job['id'],status='completed',artifacts={'model':'example.glb'},metadata={'image_preparation':{'background_action':'kept'}})
    with TestClient(app) as client:
        response=client.post('/api/jobs/'+job['id']+'/operations',json={'operation':'refine_silhouette'})
        assert response.status_code==422 and 'máscara' in response.json()['detail']
        assert len(client.get('/api/jobs').json())==1

def test_health_advertises_available_mesh_operations(tmp_path):
    from fastapi.testclient import TestClient
    from backend.app import create_app
    with TestClient(create_app(tmp_path,start_worker=False)) as client:
        assert {'cleanup','refine_silhouette'} <= set(client.get('/api/health').json()['operations'])
