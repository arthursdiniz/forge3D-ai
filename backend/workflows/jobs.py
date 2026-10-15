import hashlib
import json
import shutil
from ..config import atomic_json


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cache_key(root, inputs):
    files = {}
    for folder in ['backend', 'blender']:
        for path in (root / folder).rglob('*.py'):
            files[path.relative_to(root).as_posix()] = sha(path)
    for folder in ['models/texture', 'models/hair', 'models/texture-face']:
        for path in (root / folder).rglob('*.json'):
            files[path.relative_to(root).as_posix()] = sha(path)
        for path in (root / folder).rglob('*'):
            if path.is_file() and path.suffix in ['.safetensors', '.pth', '.onnx', '.bin']:
                info = path.stat()
                files[path.relative_to(root).as_posix()] = {'bytes': info.st_size, 'mtime_ns': info.st_mtime_ns}
    mask = root / 'models/rembg/u2netp.onnx'
    if mask.is_file():
        files['models/rembg/u2netp.onnx'] = sha(mask)
    return hashlib.sha256(json.dumps({'inputs': inputs, 'files': files}, sort_keys=True).encode()).hexdigest()


def reusable_stage(directory, key):
    try:
        record = json.loads((directory / 'stage-cache.json').read_text(encoding='utf-8'))
        report = json.loads((directory / 'texture.json').read_text(encoding='utf-8'))
        return report.get('geometry', {}).get('equivalent') is True and record['key'] == key and {'model.glb', 'texture.json'}.issubset(record['files']) and all(
            (directory / name).resolve().is_relative_to(directory.resolve()) and sha(directory / name) == expected
            for name, expected in record['files'].items())
    except (OSError, ValueError, KeyError):
        return False


def record_cache(directory, key):
    if json.loads((directory / 'texture.json').read_text(encoding='utf-8')).get('geometry', {}).get('equivalent') is not True:
        raise RuntimeError('A base de textura não passou na verificação de geometria; cache não publicado.')
    atomic_json(directory / 'stage-cache.json', {'key': key, 'files': {
        p.relative_to(directory).as_posix(): sha(p) for p in directory.rglob('*')
        if p.is_file() and p.name not in ['stage-cache.json', 'process.log']}})


def finish_workflow(worker, job, directory, metadata, artifacts):
    workflow = json.loads((directory / 'workflow.json').read_text(encoding='utf-8'))
    workflow.update(steps=worker.timeline.report()['stages'], result='qualified' if workflow['warnings'] else 'completed')
    atomic_json(directory / 'workflow.json', workflow)
    metadata['workflow'] = workflow
    metadata['total_seconds'] = worker.timeline.report()['elapsed_seconds']
    metadata['warnings'] = list(dict.fromkeys(metadata.get('warnings', []) + workflow['warnings']))
    artifacts['workflow'] = worker.artifact(job, 'workflow.json')
    return metadata, artifacts


def process_texture_workflow(worker, job, directory, options_file):
    from ..texture_engine.jobs import texture_metadata, publish_independent
    from ..texture_engine.providers import TextureProvider
    identifier = job['id']
    parent = worker.store.get(job['parent'])
    if not parent or parent['status'] != 'completed':
        raise RuntimeError('O modelo de origem não está pronto.')
    source = worker.store.directory(parent['id']) / 'model.glb'
    workflow = json.loads((directory / 'workflow.json').read_text(encoding='utf-8'))
    source_hash = sha(source)
    if source_hash != workflow['source_sha256']:
        raise RuntimeError('O arquivo de origem mudou após a solicitação; gere uma nova tentativa.')
    provider = TextureProvider(worker.root, job['options']['provider'])
    preflight = provider.preflight(job['options'])
    worker.record_stage(identifier, 'Preparando referências e materiais', 'generating')
    if preflight:
        worker.store.update(identifier, metadata={**worker.store.get(identifier)['metadata'], 'gpu_preflight': preflight})
    references = json.loads((directory / 'texture_references.json').read_text(encoding='utf-8'))
    inputs = {'source': source_hash, 'options': job['options'], 'references': {
        name: sha(directory / record['path']) for name, record in references['views'].items()}}
    key = cache_key(worker.root, inputs)
    base = directory / 'base'
    retry = workflow.get('retry_of')
    cached = worker.store.directory(retry) / 'base' if retry else None
    if cached and reusable_stage(cached, key):
        if job['options']['provider'] == 'neural_multiview':
            from ..texture_engine.neural import verify_resources
            verify_resources()
        shutil.copytree(cached, base)
        worker.record_stage(identifier, 'Base validada recuperada da tentativa anterior')
        workflow['cache_reused'] = True
    else:
        base.mkdir()
        shutil.copytree(directory / 'references', base / 'references')
        shutil.copy2(directory / 'texture_references.json', base / 'texture_references.json')
        native = base / 'options.json'
        atomic_json(native, job['options'])
        worker.run_process(provider.command(source, base, native), base, 3600, read_stages=True)
        record_cache(base, key)
        workflow['cache_reused'] = False
    selected = base
    if (worker.root / '.venv-hair/Scripts/python.exe').is_file():
        worker.record_stage(identifier, 'Verificando correspondência e proteção de detalhes')
        auto = directory / 'automatic'; auto.mkdir()
        try:
            worker.run_process([str(worker.root / '.venv-hair/Scripts/python.exe'),
                str(worker.root / 'backend/workflows/texture_cli.py'), '--input', str(base / 'model.glb'),
                '--output', str(auto), '--references', str(base / 'prepared_references'),
                '--axis', job['options']['front_axis'], '--goal', workflow['settings']['goal']], auto, 900, read_stages=True)
            automatic = json.loads((auto / 'automatic.json').read_text(encoding='utf-8'))
        except (RuntimeError, OSError, ValueError) as error:
            if worker.store.get(identifier)['status'] == 'cancelled' or worker.stop_event.is_set():
                raise
            automatic = {'accepted': False, 'human_reviewed': False,
                'warnings': ['A análise opcional não pôde terminar. A textura base validada foi preservada.'], 'detail': str(error)[-1500:]}
            atomic_json(auto / 'automatic.json', automatic)
        workflow['automatic'] = automatic
        workflow['warnings'] += automatic['warnings']
        if automatic['accepted']:
            selected = auto / 'refined'
    else:
        workflow['warnings'].append('Análise de retrato indisponível; a base de textura foi preservada. Correções locais estão nas opções avançadas.')
    # Only publish after all indispensable stages. Private stage outputs stay inspectable.
    for name in ['model.glb', 'texture.json']:
        shutil.copy2(selected / name, directory / name)
    shutil.copytree(selected / 'textures', directory / 'textures')
    for name in ['neural.json', 'gpu_monitor.json']:
        if (base / name).is_file():
            shutil.copy2(base / name, directory / name)
    texture = json.loads((directory / 'texture.json').read_text(encoding='utf-8'))
    base_texture = json.loads((base / 'texture.json').read_text(encoding='utf-8'))
    if base_texture.get('neural'):
        texture['neural'] = base_texture['neural']
    texture['workflow_base_provider'] = job['options']['provider']
    atomic_json(directory / 'texture.json', texture)
    if sha(source) != source_hash:
        raise RuntimeError('O arquivo original mudou durante a texturização.')
    metadata = texture_metadata(parent['metadata'], texture, job['options'], source_hash)
    if preflight:
        metadata['gpu_preflight'] = preflight
    artifacts = {'before': parent['artifacts']['model'], 'texture_report': worker.artifact(job, 'texture.json')}
    for record in texture['materials']:
        for channel, path in record['maps'].items():
            artifacts[f"{record['geometry']}_{channel}"] = worker.artifact(job, path)
    if (directory / 'neural.json').is_file():
        artifacts['neural_report'] = worker.artifact(job, 'neural.json')
    if (directory / 'gpu_monitor.json').is_file():
        artifacts['gpu_monitor'] = worker.artifact(job, 'gpu_monitor.json')
    if (directory / 'automatic/automatic.json').is_file():
        artifacts['automatic_report'] = worker.artifact(job, 'automatic/automatic.json')
        for path in (directory / 'automatic/masks').rglob('*.png'):
            relative = path.relative_to(directory).as_posix()
            artifacts[relative.replace('/', '__').replace('.png', '')] = worker.artifact(job, relative)
    atomic_json(directory / 'workflow.json', workflow)
    publish_independent(worker, job, directory, options_file, metadata, artifacts)
