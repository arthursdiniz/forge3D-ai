"""Enable native multiview only after local inference/render/export evidence."""
import json
from pathlib import Path
from .quality_settings import generation_settings

MODEL_REV='3a761b539b29fe4ff64714813aa9560fd66f5de0'
CODE_REV='f8db63096c8282cb27354314d896feba5ba6ff8a'
VIEW_NAMES=('front','left','back','right')

def validate_native_views(references):
    if 'front' not in references or len(references)<2 or any(name not in VIEW_NAMES for name in references):
        raise ValueError('Multiview nativo exige frente e ao menos uma vista nomeada lateral/costas, sem colagens.')
    return [name for name in VIEW_NAMES if name in references]

class HunyuanMVProvider:
    def __init__(self,root):self.root=Path(root);self.python=self.root/'.venv-hy/Scripts/python.exe'
    def health_check(self):
        directory=self.root/'models/hunyuan-mv';ready=False;view_counts=[]
        try:
            weights=json.loads((directory/'download_manifest.json').read_text())
            proof=json.loads((directory/'validation.json').read_text())
            ready=weights['download_complete'] and weights['revision']==MODEL_REV and weights['code_revision']==CODE_REV
            ready=ready and all((directory/item['path']).is_file() and (directory/item['path']).stat().st_size==item['bytes'] for item in weights['files'])
            ready=ready and proof.get('passed') is True and proof.get('weight_revision')==MODEL_REV and proof.get('code_revision')==CODE_REV and proof.get('profile')==generation_settings('balanced','hunyuan_mv')
            ready=ready and self.python.is_file() and (self.root/'backend/inference_mv.py').is_file() and (self.root/'vendor/Hunyuan3D-2/hy3dgen/shapegen/pipelines.py').is_file()
            view_counts=proof.get('validated_view_counts',[]) if ready else []
        except (OSError,ValueError,KeyError):ready=False
        return {'id':'hunyuan_mv','name':'Hunyuan3D 2mv · múltiplas vistas','available':bool(ready and view_counts),'presets':['balanced'] if ready else [],'modes':['multi-view-to-3d'],'multi_view':True,'validated_view_counts':view_counts,'outputs':['glb'],'uvs':True,'native_uvs':False,'textures':False,'native_textures':False,'pbr':False,'seed_supported':True,'quality_mode':True,'estimated_vram_gb':6,'required_free_mb':6000,'cpu_offload_validated':False,'license':'Tencent Hunyuan Community','notes':'Vistas reais nomeadas condicionam o modelo nativo. Balanced256, FP16, sem offload. Não gera rig/texturas; licença Tencent para uso pessoal local.' if ready else 'Pesos públicos presentes; validação do adaptador local pendente.'}
    def command(self,image,directory,options):
        if not self.health_check()['available']:raise RuntimeError('Multiview local ainda não validado.')
        return [str(self.python),str(self.root/'backend/inference_mv.py'),'--image',str(image),'--output',str(directory),'--options',str(options)]
