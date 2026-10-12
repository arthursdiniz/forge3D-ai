import pytest


def test_gpu_preflight_and_oom_are_explicit_without_loading_torch():
    from backend.gpu_manager import validate_vram,classify_failure
    with pytest.raises(RuntimeError,match='VRAM'):validate_vram({'total_mb':8188,'used_mb':7600},1800)
    assert validate_vram({'total_mb':8188,'used_mb':1800},1800)['free_mb']==6388
    assert classify_failure('torch.cuda.OutOfMemoryError: CUDA out of memory.')['code']=='CUDA_OOM'
    assert classify_failure('CUDA unavailable')['code']=='CUDA_UNAVAILABLE'


def test_stage_timing_comes_from_actual_events_and_does_not_fabricate_percentage():
    from backend.progress import StageTimeline
    tracker=StageTimeline(clock=iter([10,12,15,17]).__next__)
    tracker.enter('load');tracker.enter('generate');tracker.enter('finish')
    report=tracker.report()
    assert report['stages'][0]['duration_seconds']==2
    assert report['stages'][1]['duration_seconds']==3
    assert report['elapsed_seconds']==7
    assert 'percent' not in report

def test_worker_blocks_insufficient_vram_before_invoking_provider(tmp_path,monkeypatch):
    from backend.worker import Worker
    from backend.storage import Store
    class Provider:
        def health_check(self):return {'available':True,'required_free_mb':5700}
        def command(self,*args):raise AssertionError('Provider must not run after VRAM rejection.')
    store=Store(tmp_path/'data');job=store.create('MV','hunyuan_mv',{'quality':'balanced'})
    worker=Worker(tmp_path,store)
    monkeypatch.setattr('backend.worker.get_provider',lambda *args:Provider())
    monkeypatch.setattr('backend.worker.gpu_health',lambda:{'name':'4060','total_mb':8188,'used_mb':7600})
    with pytest.raises(RuntimeError,match='VRAM'):worker.process_job(job)
    assert store.get(job['id'])['metadata']['gpu_preflight']['free_mb']==588

def test_worker_stage_measurement_keeps_existing_metadata(tmp_path):
    from backend.worker import Worker
    from backend.storage import Store
    store=Store(tmp_path/'data');job=store.create('Test','triposr',{})
    store.update(job['id'],metadata={'reference':'preserved'})
    worker=Worker(tmp_path,store);worker.record_stage(job['id'],'Preparing')
    current=store.get(job['id'])
    assert current['stage']=='Preparing' and current['metadata']['reference']=='preserved'
    assert current['metadata']['timing']['elapsed_seconds']>=0
