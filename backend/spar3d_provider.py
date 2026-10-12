"""Restricted weights/toolchain remain explicit setup gates, never silent fallback."""
import json
from pathlib import Path
class SPAR3DProvider:
    def __init__(self,root):self.root=Path(root);self.python=self.root/'.venv-spar/Scripts/python.exe'
    def health_check(self):
        weights=self.root/'models/spar3d';missing=[]
        if not all((weights/name).is_file() for name in ['model.safetensors','config.yaml','license_acceptance.json']):missing.append('accepted local weights')
        if not self.python.is_file():missing.append('isolated .venv-spar with tested CUDA texture-baker extensions')
        if not (self.root/'vendor/SPAR3D/spar3d/system.py').is_file():missing.append('pinned upstream code')
        try:proof=json.loads((weights/'validation.json').read_text());validated=proof.get('passed') is True and proof.get('native_inference') is True and proof.get('fbx_passed') is True and proof.get('low_vram_validated') is True
        except (OSError,ValueError):validated=False
        if not validated:missing.append('actual local inference/export/VRAM proof')
        return {'id':'spar3d','name':'SPAR3D · gated / setup pendente','available':not missing,'missing':missing,'setup_status':'blocked_access_and_runtime' if missing else 'validated','modes':['image-to-3d'],'multi_view':False,'native_uvs':True,'native_textures':True,'textures':True,'pbr':True,'seed_supported':False,'presets':['balanced'] if not missing else [],'low_vram_official_mb':7168,'estimated_vram_gb':7,'required_free_mb':7300,'cpu_offload_validated':validated,'license':'Stability AI Community; gated access must be approved by user','notes':'Pesos gated sem autorização de acesso; não baixados. Low VRAM oficial ~7GB, ainda não medido nesta4060/Windows. Exige extensão CUDA texture-baker compilada/validada.'}
    def command(self,image,directory,options):
        if not self.health_check()['available']:raise RuntimeError('SPAR3D bloqueado: aceite/acesso aos pesos e extensão CUDA/Windows não validados. Sem fallback.')
        return [str(self.python),str(self.root/'backend/inference_spar3d.py'),'--image',str(image),'--output',str(directory),'--options',str(options)]
