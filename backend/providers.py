from pathlib import Path
from typing import Protocol
import json
import subprocess

class ModelProvider(Protocol):
    def health_check(self) -> dict: ...
    def command(self, image: Path, directory: Path, options: Path) -> list[str]: ...

class TripoSRProvider:
    def __init__(self, root):
        self.root = Path(root)
        self.python = self.root / '.venv-ai/Scripts/python.exe'

    def health_check(self):
        missing = [str(path.relative_to(self.root)) for path in [self.python,self.root/'models/triposr/model.ckpt',self.root/'models/triposr/config.yaml',self.root/'models/dino/config.json',self.root/'vendor/TripoSR/tsr/system.py'] if not path.exists()]
        for library in ['xatlas','moderngl']:
            if not any((self.root/'.venv-ai/Lib/site-packages').glob(library+'*')):missing.append('Dependência '+library)
        return {'id':'triposr','name':'TripoSR · pipeline v2','available':not missing,'missing':missing,'modes':['image-to-3d'],'outputs':['glb'],'uvs':True,'textures':'Base Color neural por texel (Balanced/Quality); cores de vértices (Fast)','pbr':False,'multi_view':False,'seed_supported':False,'estimated_vram_gb':4,'presets':['fast','balanced','quality'],'license':'MIT','notes':'Uma imagem; UV xatlas e normais explícitas. Iluminação da referência permanece incorporada. Sem rig.'}

    def command(self, image, directory, options):
        return [str(self.python),str(self.root/'backend/inference_v2.py'),'--image',str(image),'--output',str(directory),'--options',str(options)]

class TripoSGProvider:
    def __init__(self,root):
        self.root=Path(root)
        self.python=self.root/'.venv-sg/Scripts/python.exe'

    def health_check(self):
        from .quality_settings import TRIPOSG_BALANCED,TRIPOSG_QUALITY
        validation=self.root/'models/triposg/validation.json'
        try:
            proof=json.loads(validation.read_text())
            validated=proof.get('passed') is True and proof.get('code_revision')=='fc5c40990181e2a756c4e0b1c2f4d6b5202faf8c' and proof.get('weight_revision')=='2c1c516d22d58db486a058d98d31bb6177344e06'
            validated=validated and all(proof.get('validated_profile',{}).get(key)==value for key,value in TRIPOSG_BALANCED.items())
        except (OSError,ValueError):validated=False
        manifest=self.root/'models/triposg/download_manifest.json'
        try:
            weights=json.loads(manifest.read_text())
            downloaded=weights.get('download_complete') is True and weights.get('revision')=='2c1c516d22d58db486a058d98d31bb6177344e06'
            downloaded=downloaded and all((self.root/'models/triposg'/file['path']).is_file() and (self.root/'models/triposg'/file['path']).stat().st_size==file['bytes'] for file in weights['files'])
        except (OSError,ValueError,KeyError):downloaded=False
        vendor=self.root/'vendor/TripoSG/triposg'
        code_present=all((vendor/path).is_file() for path in ['pipelines/pipeline_triposg.py','models/autoencoders/autoencoder_kl_triposg.py','models/autoencoders/vae.py','models/transformers/triposg_transformer.py'])
        ready=validated and downloaded and code_present and self.python.exists() and (self.root/'backend/inference_sg.py').exists()
        try:
            quality=json.loads((self.root/'models/triposg/quality_validation.json').read_text())
            quality_ready=ready and quality.get('passed') is True and quality.get('code_revision')==proof['code_revision'] and quality.get('weight_revision')==proof['weight_revision'] and all(quality.get('validated_profile',{}).get(key)==value for key,value in TRIPOSG_QUALITY.items())
        except (OSError,ValueError,KeyError,UnboundLocalError):quality_ready=False
        presets=['balanced']+(['quality'] if quality_ready else [])
        notes=('Geometria sem textura; UV/material neutro via Blender. Seed, Balanced256³'+(' e Quality512³ validados.' if quality_ready else ' validado.')) if ready else ('Pesos oficiais baixados/verificados; inferência/integração em validação.' if downloaded else 'Download oficial ainda não concluído.')
        return {'id':'triposg','name':'TripoSG · geometria','available':ready,'modes':['image-to-3d'],'outputs':['glb'],'uvs':True,'native_uvs':False,'textures':False,'native_textures':False,'pbr':False,'multi_view':False,'seed_supported':True,'presets':presets,'estimated_vram_gb':8,'cpu_offload_validated':False,'license':'MIT','notes':notes,'validation_file':str(validation)}

    def command(self,image,directory,options):
        if not self.health_check()['available']:
            raise RuntimeError('TripoSG ainda não instalado e validado localmente. Não há fallback simulado.')
        return [str(self.python),str(self.root/'backend/inference_sg.py'),'--image',str(image),'--output',str(directory),'--options',str(options)]

def get_provider(identifier,root):
    from .hunyuan_provider import HunyuanMiniProvider
    from .hunyuan_mv_provider import HunyuanMVProvider
    from .character_base_provider import CharacterBaseProvider
    from .spar3d_provider import SPAR3DProvider
    registry={'triposr':TripoSRProvider,'triposg':TripoSGProvider,'hunyuan_mini':HunyuanMiniProvider,'hunyuan_mv':HunyuanMVProvider,'character_base_mesh':CharacterBaseProvider,'spar3d':SPAR3DProvider}
    if identifier not in registry:raise ValueError('Provedor desconhecido.')
    return registry[identifier](root)

def provider_statuses(root):
    return [get_provider(identifier,root).health_check() for identifier in ['triposr','triposg','hunyuan_mini','hunyuan_mv','spar3d']]+[
        {'id':'sf3d','name':'Stable Fast 3D','available':False,'notes':'Pesos gated (HTTP 401). Acesso/licença pendentes; inferência não validada.'},
        {'id':'trellis2','name':'TRELLIS.2 · futuro','available':False,'notes':'Upstream Linux/≥24GB recomendado; fora do perfil Windows/RTX4060 8GB. Nenhuma instalação automática.'},
    ]

def blender_path(root):
    from .config import resolve_blender
    return resolve_blender(root)

def gpu_health():
    from .gpu_manager import probe_gpu
    return probe_gpu()
