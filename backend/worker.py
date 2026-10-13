import json
import os
import re
import shutil
import subprocess
import threading
import time
import zipfile
from pathlib import Path
from .providers import get_provider, blender_path, gpu_health
from .progress import StageTimeline
from .gpu_manager import validate_vram,classify_failure

def version_warnings(old,new):
    carried=[warning for warning in old if not re.match(r'^\d+ (triângulos de área quase zero|componentes desconectados|arestas não manifold)',warning)]
    return list(dict.fromkeys(carried+new))

def version_metadata(parent,kind):
    result=dict(parent)
    if kind=='transform':
        result.pop('refinement',None);result.pop('mesh_refinement',None)
        result.pop('character_quality',None)
    return result

class Worker:
    def __init__(self, root, store):
        self.root=Path(root)
        self.store=store
        self.stop_event=threading.Event()
        self.process=None
        self.current=None
        self.timeline=StageTimeline()
        self.thread=threading.Thread(target=self.run,daemon=True,name='Forge3D-serial-worker')

    def start(self):
        self.store.recover()
        self.thread.start()

    def record_stage(self,identifier,name,status=None):
        self.timeline.enter(name)
        record=self.store.get(identifier)
        changes={'stage':name,'metadata':{**record['metadata'],'timing':self.timeline.report()}}
        if status:changes['status']=status
        return self.store.update(identifier,**changes)

    def close(self):
        self.stop_event.set()
        self.terminate()
        self.thread.join(timeout=8)

    def terminate(self):
        process=self.process
        if process and process.poll() is None:
            if os.name=='nt':
                subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],capture_output=True,timeout=15)
            else:
                process.kill()

    def run_process(self,command,directory,timeout,read_stages=False):
        env=os.environ.copy()
        env.pop('PYTHONPATH',None)
        env.update(PYTHONUTF8='1',OMP_NUM_THREADS='6',HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1')
        with (directory/'process.log').open('a',encoding='utf-8') as log:
            if self.store.get(self.current)['status']=='cancelled':
                raise RuntimeError('Processamento cancelado.')
            log.write('\nCOMMAND '+repr(command)+'\n')
            self.process=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,cwd=self.root,env=env,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
            started=time.monotonic()
            last_sample=-5
            samples=[]
            while self.process.poll() is None:
                if self.stop_event.wait(0.4) or self.store.get(self.current)['status']=='cancelled':
                    self.terminate()
                    raise RuntimeError('Processamento cancelado.')
                if time.monotonic()-started>timeout:
                    self.terminate()
                    raise RuntimeError('Tempo limite excedido. Veja process.log.')
                elapsed=time.monotonic()-started
                if read_stages and elapsed-last_sample>=2:
                    sample=gpu_health()
                    samples.append({'seconds':round(elapsed,2),'gpu_used_mb':sample['used_mb'],'gpu_total_mb':sample['total_mb']})
                    record=self.store.get(self.current)
                    self.store.update(self.current,metadata={**record['metadata'],'live_gpu':sample,'timing':self.timeline.report()})
                    last_sample=elapsed
                # Stage comes from actual worker output, never a timer percentage.
                log.flush()
                tail=(directory/'process.log').read_text(encoding='utf-8',errors='replace')[-6000:]
                for line in reversed(tail.splitlines()) if read_stages else []:
                    try:
                        value=json.loads(line)
                        if 'stage' in value:
                            record=self.store.get(self.current)
                            if record['stage']!=value['stage']:
                                self.record_stage(self.current,value['stage'])
                            break
                    except (ValueError,TypeError):
                        pass
            code=self.process.returncode
            self.process=None
            if samples:
                (directory/'gpu_monitor.json').write_text(json.dumps({'scope':'GPU total incluindo desktop e outros aplicativos; pico PyTorch em inference.json','samples':samples},indent=2),encoding='utf-8')
        if code:
            tail=(directory/'process.log').read_text(encoding='utf-8',errors='replace')[-3000:]
            raise RuntimeError('Processamento falhou. '+tail)

    def blender(self,source,directory,mode,options_file):
        executable=blender_path(self.root)
        if not executable:
            raise RuntimeError('Blender ausente. Execute Setup-Forge3D.')
        self.run_process([str(executable),'--background','--factory-startup','--disable-autoexec','--threads','6','--python-exit-code','1','--python',str(self.root/'blender/pipeline.py'),'--','--input',str(source),'--output',str(directory),'--mode',mode,'--options',str(options_file)],directory,1800)

    def artifact(self,job,name):
        path=self.store.directory(job['id']) / name
        if not path.exists():
            raise RuntimeError('Artifact ausente: '+name)
        return f"/api/files/{job['id']}/{name}"

    def diagnose_character(self,directory,metadata,interpretation=None,category='humanoid'):
        """CPU reports are measured independently of the provider's CUDA process."""
        python=self.root/'.venv-geometry/Scripts/python.exe'
        if not python.is_file():raise RuntimeError('Ambiente GeometryIntegrity ausente; execute setup local.')
        from .config import atomic_json
        refs=directory/'references.json'
        if not refs.exists():
            source=directory/'prepared_masked.png'
            if not source.exists():source=directory/'source.png'
            atomic_json(refs,{'conditioning':'front_only','views':{'front':{'path':str(source.resolve())}}})
        bundle=json.loads(refs.read_text(encoding='utf-8'))
        if (directory/'prepared_masked.png').is_file():
            bundle['views']['front']['masked_path']=str((directory/'prepared_masked.png').resolve());atomic_json(refs,bundle)
        command=[str(python),str(self.root/'backend/quality_report_cli.py'),'--input',str(directory/'model.glb'),'--output',str(directory/'character_quality.json'),'--references',str(refs),'--front-axis',metadata.get('render_front_axis','x'),'--up-axis','Y','--surface-probes']
        if interpretation and interpretation.exists():command+=['--interpretation',str(interpretation)]
        detector=self.root/'.venv-character/Scripts/python.exe'
        if interpretation and detector.is_file():
            pose_dir=directory/'candidate_pose';pose_dir.mkdir(exist_ok=True)
            self.run_process([str(detector),str(self.root/'backend/character_analysis_runtime.py'),'--image',str(directory/'qa_front.png'),'--output',str(pose_dir),'--category',category],directory,60)
            pose=json.loads((pose_dir/'analysis.json').read_text(encoding='utf-8'));pose['view']='front';pose['view_source']='known canonical model render'
            atomic_json(pose_dir/'analysis.json',pose);command+=['--candidate-pose',str(pose_dir/'analysis.json')]
        self.record_stage(self.current,'GeometryIntegrity: contornos, orientação e interseções','postprocessing')
        self.run_process(command,directory,180)
        return json.loads((directory/'character_quality.json').read_text(encoding='utf-8'))

    def publish_candidates(self,job,parent_artifacts=None,parent_metadata=None):
        directory=self.store.directory(job['id'])
        manifest=json.loads((directory/'candidates.json').read_text(encoding='utf-8'))
        if self.store.get(job['id'])['status']=='cancelled':raise RuntimeError('Lote cancelado.')
        paths=[Path(item['directory']).resolve() for item in manifest['candidates']]
        expected=(job['options'].get('candidate_count') or 3) if job['options'].get('quality_mode') else 2
        if len(paths)!=expected or len(set(paths))!=expected or any(not path.is_relative_to(directory.resolve()) or path==directory.resolve() for path in paths):raise ValueError('Diretório/quantidade de candidato inválido.')
        created=[];choices=[]
        try:
            for index,(candidate,path) in enumerate(zip(manifest['candidates'],paths)):
                if self.store.get(job['id'])['status']=='cancelled':raise RuntimeError('Lote cancelado.')
                child=self.store.create(job['name']+f' · Candidato {index+1}',job['provider'],{**job['options'],'quality':'quality' if job['options'].get('quality')=='advanced' else job['options']['quality'],'quality_mode':False,'candidate_count':None,'seed':candidate['seed'],'reference_texture':'none','refine_reference':False},parent=job['id'],initial_status='uploading')
                created.append(child['id']);target=self.store.directory(child['id'])
                shutil.copytree(path,target,dirs_exist_ok=True)
                metadata=json.loads((target/'inference.json').read_text(encoding='utf-8'))
                artifacts={key:self.artifact(child,name) for key,name in [('model','model.glb'),('original','original.glb'),('raw','raw_generation.glb'),('source','source.png'),('prepared','prepared.png'),('preview','qa_front.png'),('front','qa_front.png'),('side','qa_side.png'),('rear','qa_rear.png'),('three_quarter','qa_three_quarter.png'),('inference','inference.json'),('preparation','preparation.json'),('mesh_report','mesh_report.json')]}
                if (target/'prepared_encoder.png').exists():artifacts['prepared']=self.artifact(child,'prepared_encoder.png')
                if (target/'prepared_masked.png').is_file():artifacts['masked_reference']=self.artifact(child,'prepared_masked.png')
                if (target/'untextured_model.glb').exists():artifacts['untextured']=self.artifact(child,'untextured_model.glb')
                if (target/'qa_side_opposite.png').exists():artifacts['side_opposite']=self.artifact(child,'qa_side_opposite.png')
                if (target/'character_quality.json').exists():
                    artifacts['character_quality']=self.artifact(child,'character_quality.json')
                    metadata['character_quality']=json.loads((target/'character_quality.json').read_text(encoding='utf-8'))
                metadata.update(candidate_index=index,advanced=manifest['advanced'],mesh_version='processed_mesh',versions={'raw_generation':artifacts['raw'],'processed_mesh':artifacts['model'],'game_optimized':None,'unity_export':None})
                if self.store.get(job['id'])['status']=='cancelled':raise RuntimeError('Lote cancelado.')
                self.store.update(child['id'],stage='Candidato preparado',artifacts=artifacts,metadata=metadata)
                choices.append({'id':child['id'],'seed':candidate['seed'],'preview':artifacts['preview'],'triangles':metadata['triangles']})
            self.store.complete_candidate_batch(job['id'],created,choices,parent_metadata if parent_metadata is not None else job['metadata'],parent_artifacts if parent_artifacts is not None else job['artifacts'])
            return choices
        except Exception:
            for identifier in created:
                if self.store.get(identifier)['status']=='uploading':self.store.update(identifier,status='failed',stage='Publicação interrompida',error='Lote interrompido; arquivos preservados.')
            raise

    def process_job(self,job):
        identifier=job['id']
        self.current=identifier
        self.timeline=StageTimeline()
        self.record_stage(identifier,'Preparando tarefa local')
        directory=self.store.directory(identifier)
        options_file=directory/'options.json'
        options_file.write_text(json.dumps(job['options']),encoding='utf-8')
        if job['kind'] in ['texture','import']:
            from .texture_engine.jobs import process_independent
            process_independent(self,job,directory,options_file)
            return
        if job['kind']=='generate':
            self.record_stage(identifier,'Verificando recursos locais','generating')
            provider=get_provider(job['provider'],self.root)
            health=provider.health_check()
            if not health['available']:
                raise RuntimeError('Provedor não instalado/validado. Consulte a documentação do modelo selecionado.')
            sample=gpu_health();required=health.get('required_free_mb',{'triposr':1800,'triposg':4400,'hunyuan_mini':4800,'character_base_mesh':0}.get(job['provider'],5700))
            self.store.update(identifier,metadata={**self.store.get(identifier)['metadata'],'gpu_preflight':{**sample,'free_mb':max(0,sample['total_mb']-sample['used_mb']),'required_free_mb':required,'scope':'estimate; actual CUDA allocation can still fail'}})
            if required:validate_vram(sample,required)
            self.record_stage(identifier,'Template CPU: corpo assistido por pontos revisados' if job['provider']=='character_base_mesh' else 'Carregando IA local')
            self.run_process(provider.command(directory/'source.png',directory,options_file),directory,3600 if job['options'].get('quality_mode') else 1200,read_stages=True)
            from .reference_coordinates import record_effective_reference
            record_effective_reference(directory,job['options'])
            metadata=json.loads((directory/'inference.json').read_text())
            metadata['gpu_preflight']=self.store.get(identifier)['metadata'].get('gpu_preflight')
            blender_options={**job['options'],'texture_resolution':metadata['effective_settings'].get('texture_resolution') or 1024,'raw_up':'Y' if metadata.get('coordinate_system')=='y_up' else 'Z','geometry_only':job['options'].get('texture_output')=='geometry_only' or job['provider'] in ['triposg','hunyuan_mini','hunyuan_mv','character_base_mesh'],'front_axis':metadata.get('render_front_axis','x'),'opposite_side':True}
            options_file.write_text(json.dumps(blender_options),encoding='utf-8')
            self.store.update(identifier,status='postprocessing',stage='Blender: UVs e material neutro' if job['provider']=='triposg' else 'Blender: UVs e textura')
            neural_texture=directory/'textured_generation.glb'
            if not (directory/'candidates.json').exists():self.blender(neural_texture if neural_texture.exists() else directory/'original.glb',directory,'prepare',options_file)
            artifacts={key:self.artifact(job,name) for key,name in [('original','original.glb'),('raw','raw_generation.glb'),('model','model.glb'),('source','source.png'),('prepared','prepared.png'),('preview','qa_front.png'),('preparation','preparation.json'),('inference','inference.json'),('mesh_report','mesh_report.json')]}
            artifacts.update({view:self.artifact(job,'qa_'+view+'.png') for view in ['front','side','rear','three_quarter']})
            if neural_texture.exists():artifacts['textured_raw']=self.artifact(job,'textured_generation.glb')
            if (directory/'prepared_encoder.png').exists():
                artifacts['prepared_canvas']=artifacts['prepared']
                artifacts['prepared']=self.artifact(job,'prepared_encoder.png')
            if (directory/'gpu_monitor.json').exists():artifacts['gpu_monitor']=self.artifact(job,'gpu_monitor.json')
            if (directory/'prepared_masked.png').is_file():artifacts['masked_reference']=self.artifact(job,'prepared_masked.png')
            if (directory/'candidates.json').exists():
                metadata['candidate_index']=0
                artifacts['candidates']=self.artifact(job,'candidates.json')
                artifacts['untextured']=self.artifact(job,'untextured_model.glb')
                artifacts['side_opposite']=self.artifact(job,'qa_side_opposite.png')
            metadata['versions']={'raw_generation':artifacts['raw'],'processed_mesh':artifacts['model'],'game_optimized':None,'unity_export':None}
            metadata['mesh_version']='processed_mesh'
            if job['provider'] in ['triposg','hunyuan_mini','hunyuan_mv']:metadata['postprocessing']={'uv_unwrap':'Blender Smart UV','material':metadata['texture']['method']}
            if (directory/'qa_side_opposite.png').exists():artifacts['side_opposite']=self.artifact(job,'qa_side_opposite.png')
            if (directory/'references.json').exists():artifacts['references']=self.artifact(job,'references.json')
            if job['options'].get('quality_mode') or job['options'].get('character_mode'):
                interpretation=directory/'character_interpretation.json'
                if not interpretation.exists():interpretation=None
                manifest=json.loads((directory/'candidates.json').read_text()) if (directory/'candidates.json').exists() else None
                if manifest:
                    for candidate in manifest['candidates']:
                        candidate_dir=Path(candidate['directory']);candidate_metadata=json.loads((candidate_dir/'inference.json').read_text(encoding='utf-8'))
                        self.diagnose_character(candidate_dir,candidate_metadata,interpretation,job['options'].get('character_category','humanoid'))
                    shutil.copy2(Path(manifest['candidates'][0]['directory'])/'character_quality.json',directory/'character_quality.json')
                    metadata['character_quality']=json.loads((directory/'character_quality.json').read_text(encoding='utf-8'))
                else:metadata['character_quality']=self.diagnose_character(directory,metadata,interpretation,job['options'].get('character_category','humanoid'))
                artifacts['character_quality']=self.artifact(job,'character_quality.json')
        else:
            parent=self.store.get(job['parent'])
            if not parent or parent['status']!='completed':
                raise RuntimeError('Modelo de origem não está pronto.')
            source=self.store.directory(parent['id'])/'model.glb'
            metadata=version_metadata(parent['metadata'],job['kind'])
            if job['kind']=='transform':
                options_file.write_text(json.dumps({**job['options'],'front_axis':metadata.get('render_front_axis','x')}),encoding='utf-8')
                self.store.update(identifier,status='postprocessing',stage='Blender: '+job['options']['operation'])
                reference_operation=job['options']['operation'] in ['cleanup','refine_silhouette']
                selective_operation=job['options']['operation'] in ['symmetry','sculpt_refine','analyze_character','project_texture']
                if selective_operation or job['options']['operation']=='game_ready':
                    original=parent;visited=set()
                    while original.get('parent') and original['kind']!='generate':
                        if original['id'] in visited:raise RuntimeError('Histórico inconsistente.')
                        visited.add(original['id']);original=self.store.get(original['parent'])
                    original_dir=self.store.directory(original['id']);interpretation=original_dir/'character_interpretation.json'
                    if (original_dir/'references.json').exists():
                        shutil.copy2(original_dir/'references.json',directory/'references.json')
                        # Older assets predate independent mask provenance; upgrade only the new version.
                        if (original_dir/'prepared_masked.png').is_file():
                            from .config import atomic_json
                            refs_data=json.loads((directory/'references.json').read_text(encoding='utf-8'))
                            refs_data['views']['front']['masked_path']=str((original_dir/'prepared_masked.png').resolve())
                            atomic_json(directory/'references.json',refs_data)
                    if interpretation.exists():shutil.copy2(interpretation,directory/'character_interpretation.json')
                    if job['options']['operation']=='project_texture':
                        refs=directory/'references.json'
                        if not refs.exists():
                            reference=original_dir/'prepared_masked.png'
                            if not reference.exists():reference=original_dir/'source.png'
                            from .config import atomic_json
                            atomic_json(refs,{'views':{'front':{'path':str(reference.resolve())}}})
                        command=[str(self.root/'.venv-geometry/Scripts/python.exe'),str(self.root/'backend/reference_texture_cli.py'),'--input',str(source),'--output',str(directory),'--references',str(refs),'--resolution',str(job['options'].get('texture_resolution',1024)),'--front-axis',metadata.get('render_front_axis','x')]
                        if job['options'].get('texture_views','front')=='front':command+=['--front-only']
                        self.run_process(command,directory,300)
                        metadata['texture']=json.loads((directory/'texture_projection.json').read_text(encoding='utf-8'))
                    elif job['options']['operation']=='analyze_character':shutil.copy2(source,directory/'model.glb')
                    elif job['options']['operation']=='game_ready':self.blender(source,directory,'transform',options_file)
                    else:
                        command=[str(self.root/'.venv-geometry/Scripts/python.exe'),str(self.root/'backend/geometry_operations.py'),'--input',str(source),'--output',str(directory),'--options',str(options_file),'--front-axis',metadata.get('render_front_axis','x')]
                        if interpretation.exists():command+=['--interpretation',str(interpretation)]
                        reference=original_dir/'prepared_masked.png'
                        if not reference.exists():reference=original_dir/'source.png'
                        if reference.exists():command+=['--reference',str(reference)]
                        self.run_process(command,directory,300)
                        metadata['geometry_operation']=json.loads((directory/'geometry_operation.json').read_text(encoding='utf-8'))
                elif reference_operation:
                    original=parent;visited=set()
                    while original.get('parent'):
                        if original['id'] in visited:raise RuntimeError('Histórico inconsistente.')
                        visited.add(original['id']);original=self.store.get(original['parent'])
                        if not original:raise RuntimeError('Referência original ausente.')
                    generation_options=directory/'reference_generation_options.json'
                    generation_options.write_text(json.dumps(original['options']),encoding='utf-8')
                    command=[str(self.root/'.venv-ai/Scripts/python.exe'),str(self.root/'backend/refine_mesh.py'),'--input',str(source),'--output',str(directory),'--options',str(options_file),'--source',str(self.store.directory(original['id'])/'source.png'),'--generation-options',str(generation_options)]
                    self.run_process(command,directory,300)
                    metrics=json.loads((directory/'refinement.json').read_text())
                    metadata['mesh_refinement']=metrics
                    if 'refinement' in metrics:
                        metadata['refinement']=metrics['refinement']
                        metadata['warnings']=list(metadata.get('warnings',[]))+['Refinamento usa apenas contorno frontal estimado; não comprova anatomia, profundidade ou verso corretos.']
                else:self.blender(source,directory,'transform',options_file)
                artifacts={key:value for key,value in parent['artifacts'].items() if key in ['original','raw','source','prepared','masked_reference','preparation','inference','gpu_monitor']}
                if (selective_operation or job['options']['operation']=='game_ready') and (original_dir/'prepared_masked.png').is_file():artifacts['masked_reference']=self.artifact(original,'prepared_masked.png')
                artifacts.update(model=self.artifact(job,'model.glb'))
                if job['options']['operation']=='game_ready':
                    bake=json.loads((directory/'game_ready.json').read_text(encoding='utf-8'));metadata['game_ready']=bake
                    metadata['texture']={'method':'actual_high_to_low_bake','generated':False,'normal_baked':bake['normal_bake']['performed'],'resolution':bake['texture_resolution'],'roughness':'constant .65','metallic':'constant 0'}
                    artifacts['game_ready']=self.artifact(job,'game_ready.json')
                if reference_operation:artifacts['refinement']=self.artifact(job,'refinement.json')
                if selective_operation and (directory/'geometry_operation.json').exists():artifacts['geometry_operation']=self.artifact(job,'geometry_operation.json')
                if (directory/'texture_projection.json').exists():artifacts['texture_projection']=self.artifact(job,'texture_projection.json')
                ancestry=parent
                optimized=job['options']['operation'] in ['decimate','game_ready']
                visited=set()
                while ancestry:
                    if ancestry['id'] in visited:raise RuntimeError('Histórico inconsistente.')
                    visited.add(ancestry['id'])
                    optimized=optimized or ancestry['metadata'].get('mesh_version')=='game_optimized' or ancestry['options'].get('operation')=='decimate'
                    if not ancestry.get('parent'):break
                    ancestry=self.store.get(ancestry['parent'])
                original=ancestry or parent
                metadata['versions']=dict(parent['metadata'].get('versions') or {'raw_generation':original['artifacts'].get('raw',original['artifacts'].get('original')),'processed_mesh':original['artifacts']['model'],'game_optimized':None,'unity_export':None})
                metadata['mesh_version']='game_optimized' if optimized else 'processed_mesh'
                metadata['versions'][metadata['mesh_version']]=artifacts['model']
                self.blender(directory/'model.glb',directory,'compare',options_file)
                if selective_operation or job['options']['operation']=='game_ready':
                    interpretation=directory/'character_interpretation.json'
                    metadata['character_quality']=self.diagnose_character(directory,metadata,interpretation if interpretation.exists() else None,original['options'].get('character_category','humanoid'))
                    artifacts['character_quality']=self.artifact(job,'character_quality.json')
                    if job['options']['operation']=='game_ready':
                        source_report=directory/'source_character_quality.json'
                        command=[str(self.root/'.venv-geometry/Scripts/python.exe'),str(self.root/'backend/quality_report_cli.py'),'--input',str(source),'--output',str(source_report),'--surface-probes','--front-axis',metadata.get('render_front_axis','x')]
                        if (directory/'references.json').is_file():command+=['--references',str(directory/'references.json')]
                        self.run_process(command,directory,180)
                        from .game_ready_integrity import validate_reduction
                        metadata['game_ready']['verification']=validate_reduction(json.loads(source_report.read_text(encoding='utf-8')),metadata['character_quality'])
                        (directory/'game_ready.json').write_text(json.dumps(metadata['game_ready'],indent=2),encoding='utf-8')
                        artifacts['source_character_quality']=self.artifact(job,'source_character_quality.json')
                if reference_operation or selective_operation:
                    report=json.loads((directory/'comparison_report.json').read_text())
                    report['before']={key:parent['metadata'].get(key) for key in ['triangles','vertices','dimensions','materials']}
                    (directory/'mesh_report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
                    if (directory/'reference_prepared_alpha.png').exists():artifacts['reference_mask']=self.artifact(job,'reference_prepared_alpha.png')
                artifacts['mesh_report']=self.artifact(job,'mesh_report.json')
                artifacts.update(preview=self.artifact(job,'qa_front.png'))
                artifacts.update({view:self.artifact(job,'qa_'+view+'.png') for view in ['front','side','rear','three_quarter']})
                if (directory/'qa_side_opposite.png').is_file():artifacts['side_opposite']=self.artifact(job,'qa_side_opposite.png')
            else:
                self.store.update(identifier,status='postprocessing',stage='Blender: exportação e reimportação FBX')
                self.run_process([str(self.root/'.venv-ai/Scripts/python.exe'),str(self.root/'backend/texture_engine/export_materials.py'),'--input',str(source),'--output',str(directory/'Forge3D_Asset')],directory,180)
                self.blender(source,directory,'export',options_file)
                self.run_process([str(self.root/'.venv-ai/Scripts/python.exe'),str(self.root/'backend/texture_engine/validate_export.py'),'--source',str(source),'--directory',str(directory)],directory,180)
                self.package(job,directory,metadata)
                artifacts={'fbx':self.artifact(job,'Forge3D_Asset/Models/Model.fbx'),'unity_zip':self.artifact(job,'Forge3D_Unity.zip'),'validation':self.artifact(job,'fbx_validation.json')}
                for key,filename in [('glb','Model.glb'),('obj','Model.obj')]:
                    if (directory/'Forge3D_Asset/Models'/filename).exists():artifacts[key]=self.artifact(job,'Forge3D_Asset/Models/'+filename)
                metadata['versions']=dict(parent['metadata'].get('versions',{}))
                metadata['versions']['unity_export']=artifacts['fbx']
        report=json.loads((directory/'mesh_report.json').read_text())
        warnings=version_warnings(metadata.get('warnings',[]),report['warnings'])
        metadata.update(report['after'],warnings=warnings,before_triangles=report['before']['triangles'],blender_version=report['blender_version'])
        self.timeline.enter('Pronto');metadata['timing']=self.timeline.report()
        if job['kind']=='generate' and (directory/'candidates.json').exists():self.publish_candidates(job,artifacts,metadata)
        else:self.store.update(identifier,status='completed',stage='Pronto',metadata=metadata,artifacts=artifacts,error=None)

    def package(self,job,directory,metadata):
        package=directory/'Forge3D_Asset'
        (package/'Editor').mkdir(exist_ok=True)
        class_name='Forge3DImporter_'+job['id']
        menu='Tools/Forge3D/Import selected asset ('+job['id'][:8]+')'
        source=(self.root/'unity/Forge3DImporter.cs').read_text(encoding='utf-8')
        source=source.replace('public static class Forge3DImporter','public static class '+class_name)
        source=source.replace('Tools/Forge3D/Import selected asset package',menu)
        (package/'Editor/Forge3DImporter.cs').write_text(source,encoding='utf-8')
        shutil.copy2(self.root/'unity/README_IMPORT.md',package/'README_IMPORT.md')
        if job['provider'] in ['hunyuan_mini','hunyuan_mv']:
            for name in ['LICENSE','NOTICE']:shutil.copy2(self.root/'models'/('hunyuan-mv' if job['provider']=='hunyuan_mv' else 'hunyuan-mini')/name,package/('HUNYUAN_'+name+'.txt'))
        from .materials import texture_channels
        channels=texture_channels(package/'Textures')
        manifest={'format_version':3,'name':job['name'],'pipeline':job['options'].get('pipeline','URP'),'source_job':job['parent'],'editor_class':class_name,'editor_menu':menu,'suggested_folder':job['name'].replace(' · Unity','')+'-'+job['id'][:8],'model':'Models/Model.fbx','albedo':channels['base_color'],'normal':channels['normal'],'texture_channels':channels,'material_constants':{'roughness':.65,'metallic':0},'units':'meters','provider':job['provider'],'inference':metadata,'fbx_validation':json.loads((directory/'fbx_validation.json').read_text())}
        if (package/'materials.json').is_file():
            manifest['materials']=json.loads((package/'materials.json').read_text(encoding='utf-8'));manifest['format_version']=4
        if (directory/'geometry_export_validation.json').is_file():
            shutil.copy2(directory/'geometry_export_validation.json',package/'geometry_export_validation.json')
            manifest['geometry_export_validation']=json.loads((directory/'geometry_export_validation.json').read_text(encoding='utf-8'))
        if metadata.get('texture_provider')=='neural_multiview':
            shutil.copy2(self.root/'models/texture/sdxl/LICENSE.md',package/'SDXL_LICENSE.md')
            shutil.copy2(self.root/'vendor/MV-Adapter/LICENSE',package/'MV_ADAPTER_LICENSE.txt')
        (package/'asset_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
        with zipfile.ZipFile(directory/'Forge3D_Unity.zip','w',zipfile.ZIP_DEFLATED) as archive:
            for path in package.rglob('*'):
                if path.is_file():
                    archive.write(path,path.relative_to(directory).as_posix())

    def run(self):
        while not self.stop_event.is_set():
            job=self.store.claim_next()
            if not job:
                self.stop_event.wait(0.5)
                continue
            try:
                self.process_job(job)
            except Exception as error:
                if self.store.get(job['id'])['status']!='cancelled':
                    current=self.store.get(job['id'])
                    failure=classify_failure(error)
                    if job['kind'] in ['texture','import']:
                        from .texture_engine.errors import classify_texture_failure
                        failure=classify_texture_failure(error)
                    self.store.update(job['id'],status='failed',stage='Falha no processamento',error=str(error)[-4000:],metadata={**current['metadata'],'failure':failure,'timing':self.timeline.report()})
            finally:
                self.current=None
                self.process=None
