import torch
import pytest

@pytest.mark.skipif(not torch.cuda.is_available(),reason='Real CUDA offload regression requires GPU')
def test_offload_retains_mutable_joint_reference_cache():
    cpu_offload=pytest.importorskip('accelerate').cpu_offload
    from backend.texture_engine.neural import preserve_shared_caches
    class CacheModule(torch.nn.Module):
        def __init__(self):super().__init__();self.linear=torch.nn.Linear(2,2)
        def forward(self,values,cross_attention_kwargs):
            cross_attention_kwargs['cache_hidden_states']['layer']=self.linear(values)
            return values
    model=CacheModule();cpu_offload(model,execution_device=torch.device('cuda'))
    preserve_shared_caches(model)
    cache={};model(torch.ones((1,2),device='cuda'),cross_attention_kwargs={'cache_hidden_states':cache})
    assert 'layer' in cache and cache['layer'].device.type=='cuda'
