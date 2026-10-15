import json

def process_semantic_analysis(worker,job,directory,options_file):
    source=worker.store.directory(job['parent'])/'model.glb';worker.record_stage(job['id'],'Semântica: segmentação e superfície','generating')
    command=[str(worker.root/'.venv-hair/Scripts/python.exe'),str(worker.root/'backend/texture_engine/semantic_cli.py'),'--mode','analysis','--input',str(source),'--output',str(directory),'--options',str(options_file)];worker.run_process(command,directory,900,read_stages=True)
    report=json.loads((directory/'semantic_analysis.json').read_text());artifacts={'semantic_analysis':worker.artifact(job,'semantic_analysis.json')}
    for path in directory.rglob('*.png'):artifacts[path.relative_to(directory).as_posix().replace('/','__').replace('.png','')]=worker.artifact(job,path.relative_to(directory).as_posix())
    metadata={'semantic_analysis':report,'timing':worker.timeline.report(),'total_seconds':worker.timeline.report()['elapsed_seconds']}
    if (directory/'gpu_monitor.json').is_file():artifacts['gpu_monitor']=worker.artifact(job,'gpu_monitor.json')
    if worker.store.get(job['id'])['status']!='cancelled':worker.store.update(job['id'],status='completed',stage='Máscaras prontas para revisão',metadata=metadata,artifacts=artifacts,error=None)
