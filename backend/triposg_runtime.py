"""Official TripoSG, geometry only. No generated stand-in or downloaded auxiliary model."""
import gc
import importlib.machinery
import sys
import types
from pathlib import Path

class TripoSGRuntime:
    def __init__(self,root):self.root=Path(root);self.pipeline=None
    def load(self,offload=False,decoder_chunk=8192):
        import torch
        sys.path.insert(0,str(self.root/'vendor/TripoSG'))
        # diso is imported unconditionally upstream but ONLY called by flash
        # extraction. Disable that optional unsupported path, never substitute
        # mesh generation. The used hierarchical path is the real upstream one.
        try:import diso
        except ImportError:
            optional=types.ModuleType('diso')
            optional.__spec__=importlib.machinery.ModuleSpec('diso',loader=None)
            def unavailable(*args,**kwargs):raise RuntimeError('Flash DiffDMC indisponível neste ambiente; use extração hierárquica real.')
            optional.DiffDMC=unavailable
            sys.modules['diso']=optional
        from triposg.pipelines.pipeline_triposg import TripoSGPipeline
        class LocalPipeline(TripoSGPipeline):
            model_cpu_offload_seq='image_encoder_dinov2->transformer->vae'
        pipeline=LocalPipeline.from_pretrained(str(self.root/'models/triposg'),torch_dtype=torch.float16,local_files_only=True,use_safetensors=True,low_cpu_mem_usage=True)
        for model in [pipeline.image_encoder_dinov2,pipeline.transformer,pipeline.vae]:model.eval()
        # Upstream decode exposes num_chunks. Preserve its real field and
        # hierarchical extractor while bounding query activation size.
        original_decode=pipeline.vae._decode
        def bounded_decode(z,sampled_points,**kwargs):
            kwargs.setdefault('num_chunks',decoder_chunk)
            return original_decode(z,sampled_points,**kwargs)
        pipeline.vae._decode=bounded_decode
        if offload:pipeline.enable_model_cpu_offload(gpu_id=0)
        else:pipeline.to('cuda')
        self.pipeline=pipeline
        return pipeline
    def unload(self):
        import torch
        if self.pipeline:
            self.pipeline.maybe_free_model_hooks()
            self.pipeline=None
        gc.collect();torch.cuda.empty_cache()
