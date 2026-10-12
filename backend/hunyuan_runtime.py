"""Official pinned Hunyuan-mini shape runtime; user-authorized local license."""
from pathlib import Path
import sys

class HunyuanMiniRuntime:
    def __init__(self,root):self.root=Path(root);self.pipeline=None
    def load(self):
        import torch
        sys.path.insert(0,str(self.root/'vendor/Hunyuan3D-2'))
        from hy3dgen.shapegen import Hunyuan3DDiTFlowMatchingPipeline
        weights=self.root/'models/hunyuan-mini/hunyuan3d-dit-v2-mini'
        self.pipeline=Hunyuan3DDiTFlowMatchingPipeline.from_single_file(str(weights/'model.fp16.safetensors'),str(weights/'config.yaml'),device='cuda',dtype=torch.float16,use_safetensors=True)
        for module in [self.pipeline.model,self.pipeline.vae,self.pipeline.conditioner]:module.eval()
        return self.pipeline
    def unload(self):
        import gc,torch
        self.pipeline=None;gc.collect();torch.cuda.empty_cache()
