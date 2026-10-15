import hashlib
import json
import shutil
from .providers import TextureProvider

def texture_metadata(parent,texture,options,source_hash):
    result=dict(parent)
    history=list(parent.get('texture_provider_history',[]))
    if parent.get('texture_provider') and parent['texture_provider'] not in history:history.append(parent['texture_provider'])
    if texture['provider'] not in history:history.append(texture['provider'])
    result['texture_provider_history']=history
    resources=list(parent.get('texture_resource_history',[]))
    if texture.get('neural') or parent.get('texture',{}).get('neural') or 'neural_multiview' in history:
        for resource in ['sdxl','mv_adapter']:
            if resource not in resources:resources.append(resource)
    result['texture_resource_history']=resources
    metrics={key:result.pop(key) for key in ['peak_vram_mb','peak_reserved_mb','inference_seconds','load_seconds','total_seconds'] if key in result}
    result['geometry_generation_metrics']=dict(parent.get('geometry_generation_metrics',metrics))
    for key in ['live_gpu','gpu_preflight','failure','offline_network_blocked']:result.pop(key,None)
    result.update(seed=None,seed_supported=False)
    result.update(texture=texture,texture_provider=texture['provider'],source_model_sha256=source_hash,render_front_axis=options['front_axis'])
    if texture.get('neural'):
        neural=texture['neural'];result.update(peak_vram_mb=neural['peak_allocated_mb'],peak_reserved_mb=neural['peak_reserved_mb'],inference_seconds=neural['inference_seconds'],seed=neural['seed'],seed_supported=True,offline_network_blocked=neural['offline'])
    return result

def process_independent(worker,job,directory,options_file):
    identifier=job['id'];metadata={};artifacts={}
    if job['kind']=='import':
        from ..providers import blender_path
        source=directory/'uploads'/job['options']['filename']
        worker.record_stage(identifier,'Blender: importação estática segura','postprocessing')
        executable=blender_path(worker.root)
        if not executable:raise RuntimeError('Blender unavailable.')
        worker.run_process([str(executable),'--background','--factory-startup','--disable-autoexec','--threads','6','--python-exit-code','1','--python',str(worker.root/'blender/import_static.py'),'--','--input',str(source),'--output',str(directory)],directory,300)
        shutil.copy2(directory/'model.glb',directory/'original.glb')
        metadata={'import':json.loads((directory/'import.json').read_text(encoding='utf-8')),'render_front_axis':'negative_y','texture':{'method':'source materials or geometry-only; no generated appearance'}}
        artifacts['original']=worker.artifact(job,'original.glb');artifacts['import_report']=worker.artifact(job,'import.json')
    else:
        parent=worker.store.get(job['parent'])
        if not parent or parent['status']!='completed':raise RuntimeError('Source model is not ready.')
        source=worker.store.directory(parent['id'])/'model.glb'
        source_hash=hashlib.sha256(source.read_bytes()).hexdigest()
        provider=TextureProvider(worker.root,job['options']['provider']);preflight=provider.preflight(job['options'])
        if preflight:worker.store.update(identifier,metadata={**worker.store.get(identifier)['metadata'],'gpu_preflight':preflight})
        worker.record_stage(identifier,'Texture Engine: verificando recursos','generating')
        worker.run_process(provider.command(source,directory,options_file),directory,3600,read_stages=True)
        if hashlib.sha256(source.read_bytes()).hexdigest()!=source_hash:raise RuntimeError('Source geometry file changed.')
        texture=json.loads((directory/'texture.json').read_text(encoding='utf-8'))
        metadata=texture_metadata(parent['metadata'],texture,job['options'],source_hash)
        if preflight:metadata['gpu_preflight']=preflight
        artifacts={'before':parent['artifacts']['model'],'texture_report':worker.artifact(job,'texture.json')}
        for record in texture['materials']:
            for channel,path in record['maps'].items():artifacts[f"{record['geometry']}_{channel}"]=worker.artifact(job,path)
        if (directory/'neural.json').is_file():artifacts['neural_report']=worker.artifact(job,'neural.json')
        if texture.get('regional'):
            artifacts['candidate']=worker.artifact(job,'candidate.glb')
            for filename in ['face_reference.png','face_reference_core.png','face_reference_enlarged.png','reference_aligned.png','comparison_mask.png']+[f'face_{moment}_{view}.png' for moment in ['before','after'] for view in ['front','three_quarter','side']]:artifacts[filename.replace('.png','')]=worker.artifact(job,filename)
        if texture.get('semantic'):
            for path in directory.glob('semantic_*.png'):artifacts[path.stem]=worker.artifact(job,path.name)
        if (directory/'gpu_monitor.json').is_file():artifacts['gpu_monitor']=worker.artifact(job,'gpu_monitor.json')
    publish_independent(worker,job,directory,options_file,metadata,artifacts)

def publish_independent(worker,job,directory,options_file,metadata,artifacts):
    identifier=job['id']
    options_file.write_text(json.dumps({'front_axis':metadata['render_front_axis'],'opposite_side':True}),encoding='utf-8')
    worker.record_stage(identifier,'Blender: vistas de inspeção','postprocessing')
    worker.blender(directory/'model.glb',directory,'compare',options_file)
    report=json.loads((directory/'comparison_report.json').read_text(encoding='utf-8'))
    metadata.update(report['after'],warnings=report['warnings'],blender_version=report['blender_version'])
    artifacts.update(model=worker.artifact(job,'model.glb'),preview=worker.artifact(job,'qa_front.png'))
    artifacts.update({view:worker.artifact(job,'qa_'+view+'.png') for view in ['front','side','side_opposite','rear','three_quarter']})
    worker.timeline.enter('Pronto');metadata['timing']=worker.timeline.report()
    metadata['total_seconds']=metadata['timing']['elapsed_seconds']
    if job['kind']=='texture_workflow':
        from ..workflows.jobs import finish_workflow
        metadata,artifacts=finish_workflow(worker,job,directory,metadata,artifacts)
    worker.store.update(identifier,status='completed',stage='Pronto',metadata=metadata,artifacts=artifacts,error=None)
