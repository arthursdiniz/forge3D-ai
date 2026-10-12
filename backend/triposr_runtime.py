"""Real provider lifecycle shared by quality inference and ablation tests."""
import sys
import types
from pathlib import Path

class TripoSRRuntime:
    def __init__(self,root):
        self.root=Path(root)
        self.model=None

    def load(self):
        import torch
        from .isosurface import cpu_marching_cubes
        sys.path.insert(0,str(self.root/'vendor/TripoSR'))
        shim=types.ModuleType('torchmcubes')
        shim.marching_cubes=cpu_marching_cubes
        sys.modules['torchmcubes']=shim
        from tsr.system import TSR
        from tsr.models.tokenizers import image as tokenizer
        from omegaconf import OmegaConf
        def local_dino(repo_id,filename,**kwargs):
            if repo_id!='facebook/dino-vitb16' or filename!='config.json':raise RuntimeError('Encoder inesperado')
            return str(self.root/'models/dino/config.json')
        tokenizer.hf_hub_download=local_dino
        config=OmegaConf.load(self.root/'models/triposr/config.yaml')
        OmegaConf.resolve(config)
        self.model=TSR(config)
        weights=torch.load(self.root/'models/triposr/model.ckpt',map_location='cpu',weights_only=True)
        self.model.load_state_dict(weights)
        del weights
        self.model.eval().to('cuda')
        self.model.renderer.set_chunk_size(4096)
        return self.model

    def unload(self):
        import torch
        self.model=None
        import gc
        gc.collect()
        torch.cuda.empty_cache()
