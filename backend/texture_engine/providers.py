"""Availability is a local end-to-end proof, never merely installed weights."""
import json
import hashlib
from pathlib import Path

def runtime_valid(root,name):
    try:
        record=json.loads((root/'models/texture'/f'{name}_runtime.json').read_text(encoding='utf-8'))
        return bool(record['packages']) and all(hashlib.sha256(Path(item['metadata_path']).read_bytes()).hexdigest()==item['sha256'] for item in record['packages'])
    except (OSError,KeyError,ValueError):return False

def regional_proof_valid(root):
    try:
        proof=json.loads((root/'models/texture/region_validation.json').read_text())
        required={'backend/texture_engine/face_refinement.py','backend/texture_engine/face_projection.py','backend/texture_engine/region_camera.py','backend/texture_engine/identity.py'}
        evidence=proof.get('world_geometry',{}).get('equivalent') is True and proof.get('protected_pixels') is True and all(proof.get('exports',{}).get(name,{}).get('equivalent') is True for name in ['fbx','glb','obj'])
        return proof.get('passed') is True and evidence and required.issubset(proof['source_sha256']) and all((root/path).resolve().is_relative_to(root.resolve()) and hashlib.sha256((root/path).read_bytes()).hexdigest()==expected for path,expected in proof['source_sha256'].items())
    except (OSError,KeyError,ValueError):return False

def provider_statuses(root):
    root=Path(root)
    core=(root/'.venv-ai/Scripts/python.exe').is_file() and runtime_valid(root,'core')
    proof_file=root/'models/texture/validation.json'
    try:proof=json.loads(proof_file.read_text(encoding='utf-8'))
    except (OSError,ValueError):proof={}
    manifests=[]
    for name in ['sdxl','adapter']:
        try:manifests.append(json.loads((root/'models/texture'/name/'download_manifest.json').read_text(encoding='utf-8')))
        except (OSError,ValueError):manifests.append({})
    installed=all(item.get('download_complete') for item in manifests) and (root/'.venv-texture/Scripts/python.exe').is_file() and runtime_valid(root,'neural')
    validated=installed and proof.get('end_to_end_passed') is True and proof.get('world_geometry_equivalent') is True and proof.get('offline') is True and proof.get('conditionings')==['image','text']
    if validated:
        try:
            for relative,expected in proof['source_sha256'].items():
                path=(root/relative).resolve()
                if not path.is_relative_to(root.resolve()) or hashlib.sha256(path.read_bytes()).hexdigest()!=expected:validated=False;break
            for record in proof['resources']:
                path=(root/record['path']).resolve()
                if not path.is_relative_to(root.resolve()) or path.stat().st_size!=record['bytes'] or path.stat().st_mtime_ns!=record['mtime_ns']:validated=False;break
        except (OSError,KeyError,ValueError):validated=False
    from .semantic_resources import semantic_status
    semantic=semantic_status(root)
    return [
        {'id':'semantic_reference','name':'Reference Fidelity · semântica','available':semantic['available'],'installed':semantic['installed'],'capabilities':{'regional':True,'semantic':True,'image':True,'seed':True},'notes':'Máscaras reais/revisadas restringem projeção e composição por classes; preserva geometria e pixels protegidos.','license':'Existing MIT portrait parser; optional SDXL OpenRAIL++/adapter Apache2'},
        {'id':'reference_region','name':'Refinamento regional por referência','available':core and regional_proof_valid(root),'installed':core,'capabilities':{'regional':True,'image':True,'text':False,'seed':False,'inpainting':False},'notes':'Pixels originais, alinhamento revisado, máscara e oclusão; preserva UV/material e regiões externas.','license':'Forge core; optional anime detector MIT/Apache2'},
        {'id':'reference_projection','name':'Projeção de referência','available':core,'installed':core,'capabilities':{'named_views':['front','back','left','right'],'image':True,'text':False,'style':False,'seed':False,'fidelity':False,'resolutions':[1024,2048,4096]},'notes':'Projeção visível com máscara real; áreas ocultas neutras. Não é geração neural.','license':'Forge core / existing dependencies'},
        {'id':'neural_multiview','name':'MV-Adapter SDXL · IA multiview','available':bool(validated),'installed':installed,'required_free_mb':3000,'platform':'Windows native; local measured profile','capabilities':{'named_views':['front'],'image':True,'text':True,'style':True,'seed':True,'fidelity':True,'resolutions':[1024,2048,4096]},'notes':'Seis vistas geradas conjuntamente; albedo pode conter erros semânticos e iluminação. '+('Validado localmente.' if validated else 'Ainda sem prova local completa válida de inferência→malha→exportação; código/recursos alterados exigem revalidar.'),'license':'SDXL CreativeML Open RAIL++-M; MV-Adapter Apache-2.0','proof':proof},
        {'id':'advanced_pbr','name':'PBR avançado','available':False,'installed':False,'capabilities':{},'notes':'Nenhum backend dedicado validado; mapas de dados existentes são preservados.','license':None}]

class TextureProvider:
    def __init__(self,root,identifier):self.root=Path(root);self.identifier=identifier
    def health_check(self):return next(item for item in provider_statuses(self.root) if item['id']==self.identifier)
    def preflight(self,options):
        if not self.health_check()['available']:raise ValueError('Provedor de textura não validado localmente.')
        if self.identifier=='neural_multiview' or (self.identifier=='semantic_reference' and options.get('completion')=='neural'):
            from ..gpu_manager import probe_gpu,validate_vram
            return validate_vram(probe_gpu(),5500 if options.get('conditioning','image')=='image' else 3000)
        return None
    def prepare(self,scene,references,options,directory):
        self.session={'scene':scene,'references':references,'options':options,'directory':directory,'calibrated':None,'neural':None}
    def generate(self):
        if self.identifier=='neural_multiview':
            from .neural import generate_views
            state=self.session
            state['references'],state['calibrated'],state['neural']=generate_views(state['scene'],state['references'],state['options'],state['directory'])
        return self.session['references']
    def finalize(self):
        if self.identifier=='reference_region':
            from .face_refinement import refine_scene
            state=self.session
            return refine_scene(state['scene'],state['references']['front'],state['options'],state['directory'],state.get('source_folder'))
        from .pipeline import texture_scene
        state=self.session
        report=texture_scene(state['scene'],state['references'],state['directory'],state['options'],state['calibrated'])
        if state['neural']:
            report['neural']=state['neural'];(Path(state['directory'])/'texture.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        return report
    def release(self):
        self.session=None # CUDA/model cleanup is guaranteed by neural.generate_views finally.
    def command(self,source,directory,options_file):
        if self.identifier=='semantic_reference':
            options=json.loads(Path(options_file).read_text());analysis=self.root/'data/assets'/options['analysis_id']
            return [str(self.root/'.venv-texture/Scripts/python.exe'),str(self.root/'backend/texture_engine/semantic_cli.py'),'--mode','paint','--input',str(source),'--output',str(directory),'--options',str(options_file),'--analysis',str(analysis)]
        env='.venv-texture' if self.identifier=='neural_multiview' else '.venv-ai'
        return [str(self.root/env/'Scripts/python.exe'),str(self.root/'backend/texture_engine/cli.py'),'--input',str(source),'--output',str(directory),'--options',str(options_file)]
