"""Own assisted template capability; explicitly separate from neural engines."""
from pathlib import Path
class CharacterBaseProvider:
    def __init__(self,root):self.root=Path(root);self.python=self.root/'.venv-geometry/Scripts/python.exe'
    def health_check(self):
        from .cpu_environment import cpu_environment_ready
        return {'id':'character_base_mesh','name':'Corpo assistido · template próprio experimental','available':cpu_environment_ready(self.root,'geometry') and (self.root/'backend/character_base_mesh.py').is_file(),'presets':['balanced'],'modes':['reviewed-joints-to-body-template'],'native_textures':False,'textures':False,'seed_supported':False,'multi_view':False,'estimated_vram_gb':0,'neural_generation':False,'license':'CC0-1.0 own procedural template','notes':'Corpo volumétrico editável por pontos revisados. Sem geração neural/identidade facial/cabelo/roupas/rig; profundidade assumida.'}
    def command(self,image,directory,options):return [str(self.python),str(self.root/'backend/character_base_mesh.py'),'--image',str(image),'--output',str(directory),'--options',str(options)]
