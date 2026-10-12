import json
import pytest
from backend.storage import Store
from backend.worker import Worker

def create_batch(tmp_path,count=2):
    settings={'quality':'advanced','seed':42} if count==2 else {'quality':'balanced','quality_mode':True,'candidate_count':count,'seed':42}
    store=Store(tmp_path/'data');root=store.create('Hinata','hunyuan_mini',settings)
    directory=store.directory(root['id']);candidates=[]
    for index in range(count):
        candidate=directory/'candidates'/str(index);candidate.mkdir(parents=True)
        for name in ['original.glb','raw_generation.glb','model.glb','source.png','prepared.png','qa_front.png','qa_side.png','qa_rear.png','qa_three_quarter.png','preparation.json','mesh_report.json']:(candidate/name).write_bytes((name+str(index)).encode())
        metadata={'seed':42+index,'triangles':100+index,'texture':{'method':'none'},'warnings':[]}
        (candidate/'inference.json').write_text(json.dumps(metadata))
        candidates.append({'index':index,'seed':42+index,'directory':str(candidate)})
    (directory/'candidates.json').write_text(json.dumps({'candidates':candidates,'advanced':{'generation_wall_seconds':200}}))
    return store,root,Worker(tmp_path,store)

@pytest.mark.parametrize('count',[1,3,5])
def test_quality_batches_publish_all_candidates_atomically_without_rewriting_profile(tmp_path,count):
    store,root,worker=create_batch(tmp_path,count)
    choices=worker.publish_candidates(root)
    assert len(choices)==count
    for item in choices:
        child=store.get(item['id'])
        assert child['options']['quality']=='balanced'
        assert child['options']['quality_mode'] is False
        assert child['options']['candidate_count'] is None
        assert child['metadata']['character_candidates']==choices

def test_manifest_cannot_disagree_with_requested_candidate_count(tmp_path):
    store,root,worker=create_batch(tmp_path,3)
    file=store.directory(root['id'])/'candidates.json';manifest=json.loads(file.read_text())
    manifest['candidates'].pop();file.write_text(json.dumps(manifest))
    with pytest.raises(ValueError):worker.publish_candidates(root)
    assert len(store.list())==1

def test_publication_creates_completed_distinct_candidates_with_correct_raw_and_export_source(tmp_path):
    store,root,worker=create_batch(tmp_path)
    choices=worker.publish_candidates(root)
    assert len(choices)==2 and len({item['id'] for item in choices})==2
    for index,choice in enumerate(choices):
        child=store.get(choice['id'])
        assert child['status']=='completed' and child['parent']==root['id']
        assert child['metadata']['seed']==42+index
        assert store.directory(child['id']).joinpath('model.glb').read_bytes()==('model.glb'+str(index)).encode()
        assert child['artifacts']['raw'].startswith('/api/files/'+child['id']+'/')
    assert store.directory(root['id']).joinpath('candidates/1/model.glb').read_bytes()==b'model.glb1'

def test_cancelled_batch_cannot_publish_late_candidates(tmp_path):
    store,root,worker=create_batch(tmp_path);store.cancel(root['id'])
    with pytest.raises(RuntimeError):worker.publish_candidates(root)
    assert len(store.list())==1

def test_candidate_path_cannot_escape_its_generation_directory(tmp_path):
    store,root,worker=create_batch(tmp_path);file=store.directory(root['id'])/'candidates.json';value=json.loads(file.read_text())
    value['candidates'][0]['directory']=str(tmp_path);file.write_text(json.dumps(value))
    with pytest.raises(ValueError):worker.publish_candidates(root)
    assert len(store.list())==1


def test_cancel_during_second_candidate_copy_publishes_neither_child(tmp_path,monkeypatch):
    store,root,worker=create_batch(tmp_path)
    original_artifact=worker.artifact
    def cancel_during_second_copy(job,name):
        children=[job for job in store.list() if job['parent']==root['id']]
        if len(children)==2 and name=='model.glb':store.cancel(root['id'])
        return original_artifact(job,name)
    monkeypatch.setattr(worker,'artifact',cancel_during_second_copy)
    with pytest.raises(RuntimeError):worker.publish_candidates(root)
    assert store.get(root['id'])['status']=='cancelled'
    children=[job for job in store.list() if job['parent']==root['id']]
    assert len(children)==2 and all(job['status']!='completed' for job in children)


def test_failed_second_candidate_copy_leaves_no_completed_half_batch(tmp_path):
    store,root,worker=create_batch(tmp_path)
    (store.directory(root['id'])/'candidates/1/model.glb').unlink()
    with pytest.raises(RuntimeError):worker.publish_candidates(root)
    assert all(job['status']!='completed' for job in store.list() if job['parent']==root['id'])


def test_cancel_immediately_before_atomic_commit_keeps_all_children_unpublished(tmp_path,monkeypatch):
    store,root,worker=create_batch(tmp_path)
    complete=store.complete_candidate_batch
    def cancel_then_commit(*args,**kwargs):
        store.cancel(root['id'])
        return complete(*args,**kwargs)
    monkeypatch.setattr(store,'complete_candidate_batch',cancel_then_commit)
    with pytest.raises(RuntimeError):worker.publish_candidates(root)
    assert store.get(root['id'])['status']=='cancelled'
    assert all(job['status']!='completed' for job in store.list() if job['parent']==root['id'])
