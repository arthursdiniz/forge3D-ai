"""Shared advanced-mode contracts; candidates represent alternatives, not anatomy scores."""
def candidate_seeds(seed,count=2):
    if not isinstance(seed,int) or not 0<=seed<=4294967295:raise ValueError('Invalid base seed.')
    if count not in [1,2,3,5]:raise ValueError('Invalid candidate count.')
    return [(seed+index)%4294967296 for index in range(count)]

def finalize_model(current,directory):
    import shutil
    from pathlib import Path
    current=Path(current).resolve();target=(Path(directory)/'model.glb').resolve()
    if current!=target:shutil.copy2(current,target)

def run_advanced(root,image,output,options,settings,provider='hunyuan_mini'):
    import json,shutil,subprocess,time
    from pathlib import Path
    from .inference_hy import stage
    if provider=='hunyuan_mini':
        from .hunyuan_runtime import HunyuanMiniRuntime as Runtime
        from .inference_hy import generate_candidate
    elif provider=='hunyuan_mv':
        from .inference_mv import HunyuanMVRuntime as Runtime,generate_candidate
    elif provider=='triposg':
        from .triposg_runtime import TripoSGRuntime as Runtime
        from .inference_sg import generate_candidate
    else:raise ValueError('Provedor não suporta lote por seeds.')
    root=Path(root).resolve();image=Path(image).resolve();output=Path(output).resolve();output.mkdir(parents=True,exist_ok=True)
    if (output/'model.glb').exists():raise ValueError('Preserve existing advanced generation.')
    count=(options.get('candidate_count') or 3) if options.get('quality_mode') else 2
    started=time.perf_counter();runtime=Runtime(root)
    stage(f'Quality Mode: carregando modelo para {count} candidatos sequenciais')
    pipe=runtime.load(settings['model_cpu_offload'],settings['decoder_chunk']) if provider=='triposg' else runtime.load()
    load_seconds=time.perf_counter()-started
    candidates=[]
    try:
        for index,seed in enumerate(candidate_seeds(options.get('seed') if options.get('seed') is not None else 42,count)):
            directory=output/'candidates'/str(index);directory.mkdir(parents=True)
            candidate_options={**options,'seed':seed}
            stage(f'Quality Mode: candidato {index+1}/{count}, seed {seed}')
            for name in ['references.json','character_interpretation.json','character_interpretation_original.json']:
                if (output/name).exists():shutil.copy2(output/name,directory/name)
            metadata=generate_candidate(image,directory,candidate_options,pipe,settings,load_seconds if index==0 else 0)
            from backend.reference_coordinates import record_effective_reference
            record_effective_reference(directory,options)
            candidates.append({'index':index,'seed':seed,'directory':str(directory),'metadata':metadata})
    finally:del pipe;runtime.unload()
    return process_candidates(root,image,output,options,candidates,started)

def process_candidates(root,image,output,options,candidates,started):
    import json,shutil,subprocess,time
    from pathlib import Path
    from .inference_hy import stage
    count=len(candidates)
    from .config import resolve_blender
    blender=resolve_blender(root)
    if not blender:raise RuntimeError('Blender ausente.')
    def execute(command,directory):
        with (directory/'processing.log').open('a',encoding='utf-8') as log:
            subprocess.run([str(x) for x in command],cwd=root,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=1200,creationflags=subprocess.CREATE_NO_WINDOW)
    def process_blender(source,directory,mode,values):
        directory.mkdir(parents=True,exist_ok=True);file=directory/'blender_options.json';file.write_text(json.dumps(values),encoding='utf-8')
        execute([blender,'--background','--factory-startup','--disable-autoexec','--threads','6','--python-exit-code','1','--python',root/'blender/pipeline.py','--','--input',source,'--output',directory,'--mode',mode,'--options',file],directory)
    for candidate in candidates:
        index=candidate['index'];directory=Path(candidate['directory']);metadata=candidate['metadata']
        stage(f'Quality Mode: UVs e verificação do candidato {index+1}/{count}')
        process_blender(directory/'original.glb',directory,'prepare',{'raw_up':'Y','geometry_only':True,'front_axis':'negative_y'})
        generation_file=directory/'generation_options.json';generation_file.write_text(json.dumps(options),encoding='utf-8')
        current=directory/'model.glb'
        # Deliberately conservative, never fill holes/remesh/smooth geometry.
        operations=[] if options.get('quality_mode') else [('cleanup',{'operation':'cleanup'})]
        if options.get('refine_reference'):operations.append(('refined',{'operation':'refine_silhouette','refinement_strength':.45,'max_displacement_ratio':.03}))
        for name,values in operations:
            stage(f'Quality Mode: {name}, candidato {index+1}/{count}')
            target=directory/name;target.mkdir();file=target/'options.json';file.write_text(json.dumps(values),encoding='utf-8')
            execute([root/'.venv-ai/Scripts/python.exe',root/'backend/refine_mesh.py','--input',current,'--output',target,'--options',file,'--source',image,'--generation-options',generation_file],target)
            current=target/'model.glb'
            if name=='refined':metadata['refinement']=json.loads((target/'refinement.json').read_text())['refinement']
        shutil.copy2(current,directory/'untextured_model.glb')
        if options.get('reference_texture')=='front':
            stage(f'Quality Mode: projeção frontal, candidato {index+1}/{count}')
            import trimesh
            from PIL import Image
            from .reference_atlas import bake_reference_atlas
            if metadata['image_preparation']['background_action']=='kept':raise ValueError('Projeção exige máscara real do objeto. Use fundo automático/alpha ou desative a projeção.')
            texture_file=directory/'reference_textured.glb'
            metadata['texture']=bake_reference_atlas(trimesh.load(current,force='scene',process=False),Image.open(directory/'prepared_alpha.png'),options.get('texture_resolution') or 1024,texture_file)
            metadata['warnings'].append('Textura frontal projetada da referência; costas/oclusões permanecem neutras. Não é pintura neural/PBR; confira alinhamento nas vistas.')
            current=texture_file
        finalize_model(current,directory)
        process_blender(directory/'model.glb',directory,'compare',{'front_axis':'negative_y','opposite_side':True,'clay':options.get('reference_texture','none')=='none'})
        report=json.loads((directory/'comparison_report.json').read_text());(directory/'mesh_report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        metadata.update(report['after']);metadata['warnings']+=report['warnings']
        metadata['candidate_index']=index
        (directory/'inference.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
        (directory/'source.png').write_bytes(Path(image).read_bytes())
        candidate.update(triangles=metadata['triangles'],peak_vram_mb=metadata['peak_vram_mb'],peak_reserved_mb=metadata['peak_reserved_mb'])
    first=Path(candidates[0]['directory'])
    for path in first.iterdir():
        if path.is_file():shutil.copy2(path,output/path.name)
        elif path.name=='textures':shutil.copytree(path,output/path.name)
    metadata=dict(candidates[0]['metadata'])
    metadata['advanced']={'candidate_count':count,'selection':'first_candidate_default; human choice required, no automatic anatomy rating','shared_model_load':True,'generation_wall_seconds':round(time.perf_counter()-started,2),'peak_vram_mb':max(x['peak_vram_mb'] for x in candidates),'peak_reserved_mb':max(x['peak_reserved_mb'] for x in candidates),'refinement_integrated':bool(options.get('refine_reference')),'reference_texture':options.get('reference_texture','none')}
    (output/'inference.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
    manifest={'candidates':candidates,'advanced':metadata['advanced']}
    (output/'candidates.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    stage(f'Quality Mode: {count} candidatos reais preservados; seleção manual')
    return manifest
