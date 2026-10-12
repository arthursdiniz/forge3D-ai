import pytest
from backend.spar3d_provider import SPAR3DProvider

def test_restricted_or_unvalidated_model_never_appears_available(tmp_path):
    provider=SPAR3DProvider(tmp_path);status=provider.health_check()
    assert status['available'] is False
    assert status['setup_status']=='blocked_access_and_runtime'
    assert 'accepted local weights' in status['missing']
    assert status['low_vram_official_mb']==7168 and status['cpu_offload_validated'] is False
    with pytest.raises(RuntimeError):provider.command(tmp_path/'image.png',tmp_path,tmp_path/'options.json')
