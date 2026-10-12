"""Expose only locally proven Hunyuan-mini profiles, never a synthetic fallback."""
import json
from pathlib import Path

MODEL_REV='f90a0f7df7d5e6f71109cf333f6a95a0ae3194a6'
CODE_REV='f8db63096c8282cb27354314d896feba5ba6ff8a'

class HunyuanMiniProvider:
    def __init__(self,root):self.root=Path(root);self.python=self.root/'.venv-hy/Scripts/python.exe'
    def health_check(self):
        from .quality_settings import generation_settings
        weights=self.root/'models/hunyuan-mini';presets=[]
        try:
            manifest=json.loads((weights/'download_manifest.json').read_text());proof=json.loads((weights/'validation.json').read_text())
            downloaded=manifest.get('download_complete') is True and manifest['revision']==MODEL_REV and manifest['code_revision']==CODE_REV and all((weights/item['path']).is_file() and (weights/item['path']).stat().st_size==item['bytes'] for item in manifest['files'])
            ready=downloaded and proof.get('passed') is True and proof.get('weight_revision')==MODEL_REV and proof.get('code_revision')==CODE_REV and self.python.is_file() and (self.root/'backend/inference_hy.py').is_file() and (self.root/'vendor/Hunyuan3D-2/hy3dgen/shapegen/pipelines.py').is_file()
            if ready:presets=[mode for mode in ['balanced','quality','advanced'] if proof.get('profiles',{}).get(mode)==generation_settings(mode,'hunyuan_mini')]
        except (OSError,ValueError,KeyError):ready=False
        available=ready and bool(presets)
        return {'id':'hunyuan_mini','name':'Hunyuan3D 2mini · personagens','available':available,'presets':presets,'modes':['image-to-3d'],'outputs':['glb'],'uvs':True,'native_uvs':False,'textures':False,'native_textures':False,'reference_texture':('advanced' in presets),'pbr':False,'multi_view':False,'seed_supported':True,'estimated_vram_gb':6,'cpu_offload_validated':False,'license':'Tencent Hunyuan Community','notes':'Forma sem rig/textura nativa. Avançado preserva dois candidatos; projeção frontal opcional, verso neutro. Licença Tencent: teste pessoal local autorizado.' if available else 'Pesos públicos autorizados; perfis de inferência/exportação local ainda não validados.'}
    def command(self,image,directory,options):
        if not self.health_check()['available']:raise RuntimeError('Hunyuan-mini ainda não validado localmente.')
        return [str(self.python),str(self.root/'backend/inference_hy.py'),'--image',str(image),'--output',str(directory),'--options',str(options)]
