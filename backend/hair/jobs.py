import hashlib,json,shutil

def process_hair(worker,job,directory,options_file):
    parent=worker.store.get(job['parent']);source=worker.store.directory(parent['id'])/'model.glb';digest=hashlib.sha256(source.read_bytes()).hexdigest();analysis=job['kind']=='hair_analysis'
    worker.record_stage(job['id'],'Hair: análise local' if analysis else 'Hair: reconstrução geométrica','generating')
    command=[str(worker.root/'.venv-hair/Scripts/python.exe'),str(worker.root/'backend/hair/cli.py'),'--mode','analysis' if analysis else 'reconstruct','--input',str(source),'--output',str(directory),'--options',str(options_file)]
    if not analysis:command+=['--analysis',str(worker.store.directory(job['options']['analysis_id']))]
    worker.run_process(command,directory,240,read_stages=True)
    if hashlib.sha256(source.read_bytes()).hexdigest()!=digest:raise ValueError('Hair source changed.')
    if analysis:
        report=json.loads((directory/'hair_analysis.json').read_text());metadata={'hair_analysis':report};artifacts={'hair_analysis':worker.artifact(job,'hair_analysis.json')}
    else:
        report=json.loads((directory/'hair_geometry.json').read_text());report['base_source_asset']=parent['id'];metadata=dict(parent['metadata'])
        for key in ['peak_vram_mb','peak_reserved_mb','inference_seconds','load_seconds','total_seconds']:metadata.pop(key,None)
        metadata.update(hair=report,render_front_axis=job['options']['front_axis'])
        worker.record_stage(job['id'],'Hair: vistas de inspeção','postprocessing');options={**job['options'],'front_axis':job['options']['front_axis'],'opposite_side':True};options_file.write_text(json.dumps(options))
        worker.blender(directory/'model.glb',directory,'compare',options_file);mesh=json.loads((directory/'comparison_report.json').read_text());metadata.update(mesh['after']);metadata['warnings']=list(metadata.get('warnings',[]))+report.get('limitations',[])
        artifacts={'model':worker.artifact(job,'model.glb'),'before':parent['artifacts']['model'],'hair_report':worker.artifact(job,'hair_geometry.json'),'preview':worker.artifact(job,'qa_front.png')}
        metadata['versions']={**metadata.get('versions',{}),'processed_mesh':artifacts['model']}
    for path in directory.glob('*.png'):artifacts[path.stem]=worker.artifact(job,path.name)
    for name in ['hair_isolated.glb','scalp.glb','candidate.glb']:
        if (directory/name).is_file():artifacts[name[:-4]]=worker.artifact(job,name)
    metadata['total_seconds']=round(worker.timeline.report()['elapsed_seconds'],3)
    metadata['timing']=worker.timeline.report()
    if (directory/'gpu_monitor.json').is_file():artifacts['gpu_monitor']=worker.artifact(job,'gpu_monitor.json')
    if worker.store.get(job['id'])['status']!='cancelled':worker.store.update(job['id'],status='completed',stage='Pronto',metadata=metadata,artifacts=artifacts,error=None)
